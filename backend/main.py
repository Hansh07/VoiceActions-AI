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


# ─── Process Text Directly (graceful degradation) ───────
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
            if verification.confidence_adjustment.adjusted:
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
