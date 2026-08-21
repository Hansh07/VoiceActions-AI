"""
VoiceActions AI — Groq Service
Handles: Whisper transcription + Llama verification
"""

import time
import json
from groq import Groq
from config import GROQ_API_KEY, CONFIG
from prompts import VERIFICATION_PROMPT, VERIFICATION_PROMPT_VERSION
from models.schemas import (
    TranscriptionResult,
    VerificationResult,
    ProcessingLog,
)


client = Groq(api_key=GROQ_API_KEY)


async def transcribe_audio(audio_file_path: str) -> tuple[TranscriptionResult, ProcessingLog]:
    """
    Transcribe audio using Groq Whisper.
    Returns: (transcription_result, processing_log)
    """
    model = CONFIG["transcription"]["primary"]["model"]
    start = time.time()
    retries = 0
    max_retries = CONFIG["transcription"]["max_retries"]

    last_error = None
    while retries <= max_retries:
        try:
            with open(audio_file_path, "rb") as audio_file:
                response = client.audio.transcriptions.create(
                    file=audio_file,
                    model=model,
                    response_format="verbose_json",
                    language=None,  # Auto-detect
                )

            latency = int((time.time() - start) * 1000)

            result = TranscriptionResult(
                text=response.text,
                language=getattr(response, "language", "unknown"),
                duration_seconds=getattr(response, "duration", 0.0),
                segments=[
                    {"text": seg.get("text", ""), "start": seg.get("start", 0), "end": seg.get("end", 0)}
                    for seg in (getattr(response, "segments", None) or [])
                    if isinstance(seg, dict)
                ],
            )

            log = ProcessingLog(
                step="transcribe",
                model_used=f"groq/{model}",
                latency_ms=latency,
                retries=retries,
                estimated_cost_usd=result.duration_seconds * CONFIG["pricing"]["groq_whisper"]["per_second"],
            )

            return result, log

        except Exception as e:
            last_error = str(e)
            retries += 1
            if retries <= max_retries:
                time.sleep(1 * retries)  # Backoff

    # All retries failed
    latency = int((time.time() - start) * 1000)
    log = ProcessingLog(
        step="transcribe",
        model_used=f"groq/{model}",
        latency_ms=latency,
        retries=retries,
        error=last_error,
    )
    raise Exception(f"Transcription failed after {max_retries} retries: {last_error}")


async def verify_analysis(
    transcript: str, analysis_json: str
) -> tuple[VerificationResult, ProcessingLog]:
    """
    Use Llama to audit Gemini's analysis.
    Returns: (verification_result, processing_log)
    """
    model = CONFIG["verification"]["model"]
    start = time.time()

    try:
        user_message = f"""ORIGINAL TRANSCRIPT:
{transcript}

FIRST AI's ANALYSIS:
{analysis_json}

Please audit this analysis following the instructions."""

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": VERIFICATION_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=CONFIG["verification"]["temperature"],
            response_format={"type": "json_object"},
            max_tokens=2000,
        )

        latency = int((time.time() - start) * 1000)
        content = response.choices[0].message.content

        # Parse JSON response
        try:
            data = json.loads(content)
            result = VerificationResult(**data)
        except (json.JSONDecodeError, Exception):
            result = VerificationResult(
                audit_summary="Verification produced non-standard output",
                agreement_level="partial",
            )

        tokens_in = getattr(response.usage, "prompt_tokens", 0)
        tokens_out = getattr(response.usage, "completion_tokens", 0)

        log = ProcessingLog(
            step="verify",
            model_used=f"groq/{model}",
            tokens_input=tokens_in,
            tokens_output=tokens_out,
            latency_ms=latency,
            prompt_version=VERIFICATION_PROMPT_VERSION,
            estimated_cost_usd=(
                tokens_in * CONFIG["pricing"]["groq_llama"]["input"]
                + tokens_out * CONFIG["pricing"]["groq_llama"]["output"]
            ),
        )

        return result, log

    except Exception as e:
        latency = int((time.time() - start) * 1000)
        log = ProcessingLog(
            step="verify",
            model_used=f"groq/{model}",
            latency_ms=latency,
            error=str(e),
        )
        raise
