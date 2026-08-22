"""
VoiceActions AI — FastAPI Backend
Main application with streaming endpoints.
"""

import os
import json
import uuid
import tempfile
import asyncio
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

from config import CONFIG
from pipeline.orchestrator import process_audio
from services import supabase_service, embedding_service
from models.schemas import SearchRequest

# ─── App ─────────────────────────────────────────────────
app = FastAPI(
    title="VoiceActions AI",
    description="Voice Note → Smart Action Items with Conflict Detection",
    version="1.0.0",
)

# ─── CORS ────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Health Check ────────────────────────────────────────
@app.get("/")
async def root():
    return {
        "name": "VoiceActions AI",
        "status": "running",
        "version": "1.0.0",
        "tagline": "Speak messy. Get clarity.",
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "features": CONFIG["features"]}


# ─── Main Processing Endpoint (Streaming) ────────────────
@app.post("/api/process")
async def process_voice_note(audio: UploadFile = File(...)):
    """
    Process a voice note:
    1. Transcribe (Groq Whisper)
    2. Analyze (Gemini Flash)
    3. Verify (Groq Llama)
    4. Store (Supabase)
    
    Returns: Streamed JSON events for each pipeline step.
    """
    # Validate file
    if not audio.filename:
        raise HTTPException(status_code=400, detail="No audio file provided")
    
    # Save to temp file
    suffix = os.path.splitext(audio.filename)[1] or ".webm"
    temp_path = os.path.join(tempfile.gettempdir(), f"va_{uuid.uuid4().hex}{suffix}")
    
    try:
        content = await audio.read()
        with open(temp_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save audio: {str(e)}")
    
    # Stream results
    async def event_stream():
        step_events = []
        
        async def on_step(event: dict):
            step_events.append(event)
            yield json.dumps(event) + "\n"
        
        # We need a different approach since we can't yield from a callback
        # Use an asyncio.Queue instead
        pass
    
    # Process synchronously but return streaming-compatible response
    async def generate():
        queue = asyncio.Queue()
        
        async def on_step(event: dict):
            await queue.put(event)
        
        async def run_pipeline():
            try:
                result = await process_audio(temp_path, on_step=on_step)
                await queue.put({"step": "final_result", "data": result.model_dump()})
            except Exception as e:
                await queue.put({"step": "error", "error": str(e)})
            finally:
                await queue.put(None)  # Sentinel
                # Cleanup
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass
        
        # Start pipeline in background
        task = asyncio.create_task(run_pipeline())
        
        # Yield events as they come
        while True:
            event = await queue.get()
            if event is None:
                break
            yield json.dumps(event) + "\n"
    
    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ─── Non-streaming endpoint (simpler, for testing) ──────
@app.post("/api/process-sync")
async def process_voice_note_sync(audio: UploadFile = File(...)):
    """Synchronous version — returns complete result at once."""
    if not audio.filename:
        raise HTTPException(status_code=400, detail="No audio file provided")
    
    suffix = os.path.splitext(audio.filename)[1] or ".webm"
    temp_path = os.path.join(tempfile.gettempdir(), f"va_{uuid.uuid4().hex}{suffix}")
    
    try:
        content = await audio.read()
        with open(temp_path, "wb") as f:
            f.write(content)
        
        result = await process_audio(temp_path)
        return JSONResponse(content=result.model_dump())
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            os.unlink(temp_path)
        except Exception:
            pass


# ─── Batch Processing (Multiple Audio Files) ─────────
@app.post("/api/process-batch")
async def process_batch_audio(files: list[UploadFile] = File(...)):
    """
    Process MULTIPLE audio files at once:
    1. Transcribe each file individually (Groq Whisper)
    2. Combine all transcripts into one unified text
    3. Analyze the combined text (Gemini Flash)
    4. Verify (Groq Qwen) — catches cross-file conflicts
    5. Store (Supabase)
    
    Returns: Streamed NDJSON events for each step.
    """
    if not files or len(files) == 0:
        raise HTTPException(status_code=400, detail="No audio files provided")
    
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 files allowed per batch")
    
    # Save all files to temp paths
    temp_paths = []
    file_names = []
    for audio in files:
        suffix = os.path.splitext(audio.filename or "audio.webm")[1] or ".webm"
        temp_path = os.path.join(tempfile.gettempdir(), f"va_{uuid.uuid4().hex}{suffix}")
        try:
            content = await audio.read()
            with open(temp_path, "wb") as f:
                f.write(content)
            temp_paths.append(temp_path)
            file_names.append(audio.filename or f"Audio {len(temp_paths)}")
        except Exception as e:
            # Cleanup already-saved files
            for p in temp_paths:
                try: os.unlink(p)
                except: pass
            raise HTTPException(status_code=500, detail=f"Failed to save audio file: {str(e)}")
    
    async def generate():
        queue = asyncio.Queue()
        
        async def on_step(event: dict):
            await queue.put(event)
        
        async def run_batch_pipeline():
            from services import gemini_service, groq_service
            from models.schemas import (
                PipelineResponse, TranscriptionResult, DecisionEntry,
                ProcessingLog, AnalysisResult,
            )
            import time as time_mod
            
            pipeline_start = time_mod.time()
            decision_trace = []
            logs = []
            transcripts = []
            total_duration = 0.0
            
            # ── Step 1: Transcribe each file ──
            await queue.put({
                "step": "transcribe",
                "status": "started",
                "model": "groq/whisper-large-v3",
                "data": {"total_files": len(temp_paths), "file_names": file_names},
            })
            
            for i, (path, name) in enumerate(zip(temp_paths, file_names)):
                try:
                    await queue.put({
                        "step": "transcribe",
                        "status": "progress",
                        "data": {"current": i + 1, "total": len(temp_paths), "file": name},
                    })
                    
                    t_result, t_log = await groq_service.transcribe_audio(path)
                    logs.append(t_log)
                    
                    if t_result.text and t_result.text.strip():
                        transcripts.append({
                            "file": name,
                            "text": t_result.text.strip(),
                            "duration": t_result.duration_seconds,
                            "language": t_result.language,
                        })
                        total_duration += t_result.duration_seconds
                    
                    decision_trace.append(DecisionEntry(
                        timestamp="",
                        step=f"transcribe_file_{i+1}",
                        action="success",
                        reason=f"Transcribed '{name}' ({t_result.duration_seconds:.1f}s)",
                        model=t_log.model_used,
                        latency_ms=t_log.latency_ms,
                    ))
                    
                except Exception as e:
                    decision_trace.append(DecisionEntry(
                        timestamp="",
                        step=f"transcribe_file_{i+1}",
                        action="failed",
                        reason=f"Failed to transcribe '{name}': {str(e)}",
                    ))
            
            # Clean up temp files
            for p in temp_paths:
                try: os.unlink(p)
                except: pass
            
            if not transcripts:
                await queue.put({"step": "transcribe", "status": "error", "error": "No speech detected in any of the uploaded files"})
                await queue.put({"step": "final_result", "data": PipelineResponse(
                    transcription=TranscriptionResult(text="", language="none", duration_seconds=0),
                    analysis=AnalysisResult(summary="No speech detected in any uploaded files.", confidence=0),
                    decision_trace=decision_trace,
                    logs=logs,
                    total_latency_ms=int((time_mod.time() - pipeline_start) * 1000),
                ).model_dump()})
                await queue.put(None)
                return
            
            # Combine transcripts with labels
            combined_parts = []
            for t in transcripts:
                combined_parts.append(f"[Voice Note: {t['file']}]\n{t['text']}")
            combined_text = "\n\n---\n\n".join(combined_parts)
            
            combined_transcription = TranscriptionResult(
                text=combined_text,
                language=transcripts[0]["language"] if transcripts else "unknown",
                duration_seconds=total_duration,
            )
            
            await queue.put({
                "step": "transcribe",
                "status": "done",
                "data": {
                    "files_transcribed": len(transcripts),
                    "total_files": len(temp_paths),
                    "total_duration": total_duration,
                    "combined_length": len(combined_text),
                },
            })
            
            # ── Step 2: Analyze combined transcript ──
            await queue.put({"step": "analyze", "status": "started", "model": "gemini/gemini-2.0-flash"})
            
            analysis = None
            try:
                analysis, a_log = await gemini_service.analyze_transcript(combined_text)
                logs.append(a_log)
                decision_trace.append(DecisionEntry(
                    timestamp="",
                    step="analyze",
                    action="success",
                    reason=f"Analyzed {len(transcripts)} combined files — found {len(analysis.actions)} actions, {len(analysis.conflicts)} conflicts",
                    model=a_log.model_used,
                    latency_ms=a_log.latency_ms,
                ))
                await queue.put({"step": "analyze", "status": "done", "data": analysis.model_dump(), "log": a_log.model_dump()})
            except Exception:
                try:
                    analysis, a_log = await gemini_service.analyze_transcript_fallback(combined_text)
                    logs.append(a_log)
                    await queue.put({"step": "analyze", "status": "done", "data": analysis.model_dump(), "log": a_log.model_dump()})
                except Exception as e:
                    await queue.put({"step": "analyze", "status": "error", "error": str(e)})
                    await queue.put(None)
                    return
            
            # ── Step 3: Verify ──
            verification = None
            final_confidence = analysis.confidence if analysis else 0
            
            if CONFIG["features"]["verification_step"] and analysis:
                await queue.put({"step": "verify", "status": "started", "model": "groq/qwen-27b"})
                try:
                    analysis_json = json.dumps(analysis.model_dump(), indent=2)
                    verification, v_log = await groq_service.verify_analysis(combined_text, analysis_json)
                    logs.append(v_log)
                    if verification.confidence_adjustment.adjusted:
                        final_confidence = verification.confidence_adjustment.adjusted
                    await queue.put({"step": "verify", "status": "done", "data": verification.model_dump(), "log": v_log.model_dump()})
                except Exception:
                    await queue.put({"step": "verify", "status": "skipped"})
            
            # ── Step 4: Store ──
            await queue.put({"step": "store", "status": "started"})
            voice_note_id = None
            try:
                voice_note_id = await supabase_service.store_voice_note(
                    transcript=combined_text,
                    language=combined_transcription.language,
                    duration=combined_transcription.duration_seconds,
                )
                if analysis and voice_note_id:
                    await supabase_service.store_actions(voice_note_id, analysis.actions)
                    if analysis.conflicts:
                        await supabase_service.store_conflicts(voice_note_id, analysis.conflicts)
                await queue.put({"step": "store", "status": "done"})
            except Exception:
                await queue.put({"step": "store", "status": "skipped"})
            
            total_cost = sum(log.estimated_cost_usd for log in logs)
            total_latency = int((time_mod.time() - pipeline_start) * 1000)
            
            result = PipelineResponse(
                transcription=combined_transcription,
                analysis=analysis,
                verification=verification,
                final_confidence=final_confidence,
                total_cost_usd=total_cost,
                total_latency_ms=total_latency,
                decision_trace=decision_trace,
                logs=logs,
                voice_note_id=voice_note_id,
            )
            
            await queue.put({"step": "final_result", "data": result.model_dump()})
            await queue.put(None)
        
        task = asyncio.create_task(run_batch_pipeline())
        
        while True:
            event = await queue.get()
            if event is None:
                break
            yield json.dumps(event) + "\n"
    
    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )



class TextInput(BaseModel):
    text: str


@app.post("/api/process-text")
async def process_text_input(body: TextInput):
    """
    Process a text transcript directly (no audio).
    Graceful degradation: when mic doesn't work, paste text.
    """
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="Empty text")
    
    # Skip transcription, go straight to analysis
    from services import gemini_service, groq_service
    from models.schemas import (
        PipelineResponse, TranscriptionResult, DecisionEntry,
        VerificationResult, AnalysisResult,
    )
    import time
    
    pipeline_start = time.time()
    decision_trace = []
    logs = []
    
    # Fake transcription result
    transcription = TranscriptionResult(
        text=body.text,
        language="text-input",
        duration_seconds=0,
    )
    
    decision_trace.append(DecisionEntry(
        timestamp="",
        step="transcribe",
        action="skipped",
        reason="Text input mode — no audio to transcribe",
    ))
    
    # Analyze
    try:
        analysis, a_log = await gemini_service.analyze_transcript(body.text)
        logs.append(a_log)
    except Exception:
        try:
            analysis, a_log = await gemini_service.analyze_transcript_fallback(body.text)
            logs.append(a_log)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
    
    # Verify
    verification = None
    final_confidence = analysis.confidence
    if CONFIG["features"]["verification_step"]:
        try:
            import json as json_mod
            analysis_json = json_mod.dumps(analysis.model_dump(), indent=2)
            verification, v_log = await groq_service.verify_analysis(body.text, analysis_json)
            logs.append(v_log)
            if verification and verification.confidence_adjustment and verification.confidence_adjustment.adjusted > 0:
                final_confidence = verification.confidence_adjustment.adjusted
        except Exception:
            pass
    
    total_cost = sum(log.estimated_cost_usd for log in logs)
    total_latency = int((time.time() - pipeline_start) * 1000)
    
    return PipelineResponse(
        transcription=transcription,
        analysis=analysis,
        verification=verification,
        final_confidence=final_confidence,
        total_cost_usd=total_cost,
        total_latency_ms=total_latency,
        decision_trace=decision_trace,
        logs=logs,
    ).model_dump()


# ─── Semantic Search ─────────────────────────────────────
@app.post("/api/search")
async def search_past_actions(body: SearchRequest):
    """Search past action items using semantic similarity (pgvector)."""
    try:
        query_embedding = await embedding_service.generate_query_embedding(body.query)
        if not query_embedding:
            raise HTTPException(status_code=500, detail="Failed to generate query embedding")
        
        results = await supabase_service.search_actions(query_embedding, body.limit)
        return {"results": results, "query": body.query}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── History ─────────────────────────────────────────────
@app.get("/api/history")
async def get_history():
    """Get recent voice notes with actions and conflicts."""
    try:
        notes = await supabase_service.get_recent_voice_notes()
        return {"voice_notes": notes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Config (for frontend) ──────────────────────────────
@app.get("/api/config")
async def get_config():
    """Return feature flags for frontend."""
    return {
        "features": CONFIG["features"],
        "models": {
            "transcription": CONFIG["transcription"]["primary"]["model"],
            "analysis": CONFIG["analysis"]["primary"]["model"],
            "verification": CONFIG["verification"]["model"],
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
