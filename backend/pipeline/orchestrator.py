"""
VoiceActions AI — Pipeline Orchestrator
Hand-rolled agent loop with retries, fallbacks, and decision trace.
NO frameworks — shows the control flow explicitly (as the hackathon brief recommends).
"""

import time
import json
from datetime import datetime, timezone
from models.schemas import (
    PipelineResponse,
    DecisionEntry,
    ProcessingLog,
    AnalysisResult,
    VerificationResult,
    TranscriptionResult,
)
from services import groq_service, gemini_service, supabase_service, embedding_service
from config import CONFIG


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _trace(step: str, action: str, reason: str = "", model: str = "", latency_ms: int = 0) -> DecisionEntry:
    return DecisionEntry(
        timestamp=_now(),
        step=step,
        action=action,
        reason=reason,
        model=model,
        latency_ms=latency_ms,
    )


async def process_audio(audio_file_path: str, on_step=None) -> PipelineResponse:
    """
    Main pipeline orchestrator.
    Chains: Transcribe → Analyze → Verify → Store → Log
    
    Hand-rolled loop with:
    - Retries per step (with backoff)
    - Fallback chains (Gemini ↔ Groq)
    - Decision trace (every retry/fallback logged)
    - Observability (tokens, cost, latency per step)
    
    Args:
        audio_file_path: Path to the audio file
        on_step: Optional callback for streaming status updates
    
    Returns:
        PipelineResponse with all results
    """
    pipeline_start = time.time()
    decision_trace: list[DecisionEntry] = []
    logs: list[ProcessingLog] = []
    
    transcription = None
    analysis = None
    verification = None
    voice_note_id = None
    
    # ════════════════════════════════════════════════════════
    # STEP 1: TRANSCRIBE (Groq Whisper)
    # ════════════════════════════════════════════════════════
    if on_step:
        await on_step({"step": "transcribe", "status": "started", "model": "groq/whisper-large-v3"})
    
    decision_trace.append(_trace("transcribe", "started", model="groq/whisper-large-v3"))
    
    try:
        transcription, t_log = await groq_service.transcribe_audio(audio_file_path)
        logs.append(t_log)
        decision_trace.append(_trace(
            "transcribe", "success",
            reason=f"Transcribed {transcription.duration_seconds:.1f}s of audio, detected language: {transcription.language}",
            model=t_log.model_used,
            latency_ms=t_log.latency_ms,
        ))
        
        if on_step:
            await on_step({
                "step": "transcribe",
                "status": "done",
                "data": transcription.model_dump(),
                "log": t_log.model_dump(),
            })
            
    except Exception as e:
        decision_trace.append(_trace(
            "transcribe", "failed",
            reason=f"Groq Whisper failed: {str(e)}",
            model="groq/whisper-large-v3",
        ))
        
        # No fallback for transcription — audio input is required
        if on_step:
            await on_step({"step": "transcribe", "status": "error", "error": str(e)})
        
        return PipelineResponse(
            decision_trace=decision_trace,
            logs=logs,
            total_latency_ms=int((time.time() - pipeline_start) * 1000),
        )
    
    # Check for empty transcript
    if not transcription.text or transcription.text.strip() == "":
        decision_trace.append(_trace(
            "transcribe", "skipped",
            reason="Empty transcript — no speech detected in audio",
        ))
        if on_step:
            await on_step({"step": "analyze", "status": "skipped", "reason": "No speech detected"})
        
        return PipelineResponse(
            transcription=transcription,
            analysis=AnalysisResult(summary="No speech detected in the audio.", confidence=0),
            decision_trace=decision_trace,
            logs=logs,
            total_latency_ms=int((time.time() - pipeline_start) * 1000),
        )
    
    # ════════════════════════════════════════════════════════
    # STEP 2: ANALYZE (Gemini Flash → fallback Groq Llama)
    # ════════════════════════════════════════════════════════
    if on_step:
        await on_step({"step": "analyze", "status": "started", "model": "gemini/gemini-2.0-flash"})
    
    decision_trace.append(_trace("analyze", "started", model="gemini/gemini-2.0-flash"))
    
    try:
        analysis, a_log = await gemini_service.analyze_transcript(transcription.text)
        logs.append(a_log)
        decision_trace.append(_trace(
            "analyze", "success",
            reason=f"Found {len(analysis.actions)} actions, {len(analysis.conflicts)} conflicts, {len(analysis.ambiguities)} ambiguities",
            model=a_log.model_used,
            latency_ms=a_log.latency_ms,
        ))
        
        if on_step:
            await on_step({
                "step": "analyze",
                "status": "done",
                "data": analysis.model_dump(),
                "log": a_log.model_dump(),
            })
            
    except Exception as e:
        decision_trace.append(_trace(
            "analyze", "fallback",
            reason=f"Gemini failed ({str(e)}), falling back to Groq Llama",
            model="gemini/gemini-2.0-flash",
        ))
        
        # FALLBACK: Use Groq Llama for analysis
        try:
            if on_step:
                await on_step({"step": "analyze", "status": "fallback", "model": "groq/llama-3.3-70b"})
            
            analysis, a_log = await gemini_service.analyze_transcript_fallback(transcription.text)
            logs.append(a_log)
            decision_trace.append(_trace(
                "analyze", "success",
                reason=f"Fallback successful. Found {len(analysis.actions)} actions, {len(analysis.conflicts)} conflicts",
                model=a_log.model_used,
                latency_ms=a_log.latency_ms,
            ))
            
            if on_step:
                await on_step({
                    "step": "analyze",
                    "status": "done",
                    "data": analysis.model_dump(),
                    "log": a_log.model_dump(),
                    "fallback": True,
                })
                
        except Exception as e2:
            decision_trace.append(_trace(
                "analyze", "failed",
                reason=f"Both Gemini and Groq Llama failed: {str(e2)}",
            ))
            if on_step:
                await on_step({"step": "analyze", "status": "error", "error": str(e2)})
            
            return PipelineResponse(
                transcription=transcription,
                decision_trace=decision_trace,
                logs=logs,
                total_latency_ms=int((time.time() - pipeline_start) * 1000),
            )
    
    # ════════════════════════════════════════════════════════
    # STEP 3: VERIFY (Groq Llama audits Gemini's analysis)
    # ════════════════════════════════════════════════════════
    final_confidence = analysis.confidence
    
    if CONFIG["features"]["verification_step"] and CONFIG["verification"]["enabled"]:
        if on_step:
            await on_step({"step": "verify", "status": "started", "model": "groq/llama-3.3-70b"})
        
        decision_trace.append(_trace("verify", "started", model="groq/llama-3.3-70b-versatile"))
        
        try:
            analysis_json = json.dumps(analysis.model_dump(), indent=2)
            verification, v_log = await groq_service.verify_analysis(
                transcription.text, analysis_json
            )
            logs.append(v_log)
            
            # Apply verification adjustments
            if verification.confidence_adjustment.adjusted:
                final_confidence = verification.confidence_adjustment.adjusted
            
            # Merge missed actions into analysis
            for missed in verification.missed_actions:
                from models.schemas import ActionItem
                analysis.actions.append(ActionItem(
                    task=missed.task,
                    owner=missed.owner,
                    source_quote=missed.source_quote,
                    priority="medium",
                ))
            
            # Merge missed conflicts
            for missed in verification.missed_conflicts:
                from models.schemas import Conflict
                analysis.conflicts.append(Conflict(
                    action_a=missed.action_a,
                    action_b=missed.action_b,
                    reason=missed.reason,
                    severity="medium",
                ))
            
            # Remove false conflicts
            if verification.false_conflicts:
                false_descriptions = {fc.original_conflict for fc in verification.false_conflicts}
                analysis.conflicts = [
                    c for c in analysis.conflicts
                    if c.reason not in false_descriptions
                ]
            
            decision_trace.append(_trace(
                "verify", "success",
                reason=f"Audit: {verification.agreement_level}. Added {len(verification.missed_actions)} missed actions, removed {len(verification.false_conflicts)} false conflicts. Confidence: {analysis.confidence} → {final_confidence}",
                model=v_log.model_used,
                latency_ms=v_log.latency_ms,
            ))
            
            if on_step:
                await on_step({
                    "step": "verify",
                    "status": "done",
                    "data": verification.model_dump(),
                    "log": v_log.model_dump(),
                })
                
        except Exception as e:
            decision_trace.append(_trace(
                "verify", "skipped",
                reason=f"Verification failed ({str(e)}), proceeding with unverified analysis",
                model="groq/llama-3.3-70b-versatile",
            ))
            verification = VerificationResult(
                audit_summary="Verification skipped due to error",
                agreement_level="partial",
            )
            if on_step:
                await on_step({"step": "verify", "status": "skipped", "reason": str(e)})
    else:
        decision_trace.append(_trace("verify", "skipped", reason="Verification disabled in config"))
        if on_step:
            await on_step({"step": "verify", "status": "skipped", "reason": "Disabled"})
    
    # ════════════════════════════════════════════════════════
    # STEP 4: STORE (Supabase — DB + embeddings)
    # ════════════════════════════════════════════════════════
    if CONFIG["features"]["store_to_database"]:
        if on_step:
            await on_step({"step": "store", "status": "started"})
        
        decision_trace.append(_trace("store", "started"))
        
        try:
            # Store voice note
            voice_note_id = await supabase_service.store_voice_note(
                transcript=transcription.text,
                language=transcription.language,
                duration_seconds=transcription.duration_seconds,
            )
            
            if voice_note_id and analysis.actions:
                # Generate embeddings for actions
                action_texts = [a.task for a in analysis.actions]
                embeddings = []
                if CONFIG["features"]["semantic_search"]:
                    try:
                        embeddings = await embedding_service.generate_batch_embeddings(action_texts)
                    except Exception:
                        decision_trace.append(_trace("store", "fallback", reason="Embedding generation failed, storing without embeddings"))
                
                # Store actions with embeddings
                await supabase_service.store_actions(
                    voice_note_id,
                    [a.model_dump() for a in analysis.actions],
                    embeddings,
                )
                
                # Store conflicts
                if analysis.conflicts:
                    await supabase_service.store_conflicts(
                        voice_note_id,
                        [c.model_dump() for c in analysis.conflicts],
                    )
                
                # Store processing logs
                for log in logs:
                    await supabase_service.store_processing_log(voice_note_id, log)
            
            decision_trace.append(_trace("store", "success", reason=f"Stored voice note {voice_note_id}"))
            if on_step:
                await on_step({"step": "store", "status": "done", "voice_note_id": voice_note_id})
                
        except Exception as e:
            decision_trace.append(_trace("store", "skipped", reason=f"Database storage failed: {str(e)}"))
            if on_step:
                await on_step({"step": "store", "status": "skipped", "reason": str(e)})
    
    # ════════════════════════════════════════════════════════
    # FINAL: Build response
    # ════════════════════════════════════════════════════════
    total_cost = sum(log.estimated_cost_usd for log in logs)
    total_latency = int((time.time() - pipeline_start) * 1000)
    
    if on_step:
        await on_step({
            "step": "complete",
            "status": "done",
            "total_cost_usd": total_cost,
            "total_latency_ms": total_latency,
            "final_confidence": final_confidence,
        })
    
    return PipelineResponse(
        transcription=transcription,
        analysis=analysis,
        verification=verification,
        final_confidence=final_confidence,
        total_cost_usd=total_cost,
        total_latency_ms=total_latency,
        decision_trace=decision_trace,
        logs=logs,
        voice_note_id=voice_note_id,
    )
