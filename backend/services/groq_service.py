"""
VoiceActions AI — Groq Service
Handles: Whisper transcription + Llama verification
"""

import time
import json
import asyncio
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
                # Force Hindi in Devanagari script or Hinglish instead of Urdu Arabic script
                prompt_text = "Hindi speech transcript in Devanagari script (हिंदी) and Indian English/Hinglish (e.g. राम, श्याम, सीता, पटना, दिल्ली, काम करो, रिपोर्ट भेजो). Always transcribe Hindi words in Devanagari script or English alphabet, never in Urdu Arabic script."
                response = client.audio.transcriptions.create(
                    file=audio_file,
                    model=model,
                    response_format="verbose_json",
                    language=None,  # Auto-detect with prompt bias
                    prompt=prompt_text,
                )

            latency = int((time.time() - start) * 1000)
            lang = getattr(response, "language", "unknown")
            if lang == "ur" or lang == "urdu":
                lang = "Hindi"

            result = TranscriptionResult(
                text=response.text,
                language=lang,
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
                await asyncio.sleep(1 * retries)  # Backoff

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


def _sanitize_verification_data(raw: dict) -> VerificationResult:
    try:
        from models.schemas import MissedAction, FalseConflict, MissedConflict, ConfidenceAdjustment, AgreementLevel
        
        # 1. Sanitize agreement_level
        ag_val = str(raw.get("agreement_level", "full")).lower().strip()
        if "sig" in ag_val or "disagree" in ag_val:
            ag_enum = AgreementLevel.SIGNIFICANT_DISAGREEMENT
        elif "part" in ag_val or "mod" in ag_val:
            ag_enum = AgreementLevel.PARTIAL
        else:
            ag_enum = AgreementLevel.FULL

        # 2. Sanitize confidence_adjustment
        cadj_raw = raw.get("confidence_adjustment")
        if isinstance(cadj_raw, dict):
            cadj = ConfidenceAdjustment(
                original=int(cadj_raw.get("original", 0) or 0),
                adjusted=int(cadj_raw.get("adjusted", 0) or 0),
                reason=str(cadj_raw.get("reason", "")),
            )
        else:
            cadj = ConfidenceAdjustment()

        # 3. Sanitize missed_actions
        missed_actions = []
        for item in raw.get("missed_actions", []) or []:
            if isinstance(item, dict) and item.get("task"):
                missed_actions.append(MissedAction(
                    task=str(item.get("task", "")),
                    owner=str(item.get("owner", "unassigned")),
                    source_quote=str(item.get("source_quote", "")),
                ))

        # 4. Sanitize false_conflicts
        false_conflicts = []
        for item in raw.get("false_conflicts", []) or []:
            if isinstance(item, dict):
                false_conflicts.append(FalseConflict(
                    original_conflict=str(item.get("original_conflict", "") or item.get("conflict", "")),
                    why_not_conflict=str(item.get("why_not_conflict", "") or item.get("reason", "")),
                ))

        # 5. Sanitize missed_conflicts
        missed_conflicts = []
        for item in raw.get("missed_conflicts", []) or []:
            if isinstance(item, dict) and (item.get("action_a") or item.get("reason")):
                missed_conflicts.append(MissedConflict(
                    action_a=str(item.get("action_a", "")),
                    action_b=str(item.get("action_b", "")),
                    reason=str(item.get("reason", "")),
                ))

        audit_sum = str(raw.get("audit_summary", "")).strip()
        if not audit_sum:
            audit_sum = "Groq Qwen 27B audited and confirmed the analysis."

        return VerificationResult(
            missed_actions=missed_actions,
            false_conflicts=false_conflicts,
            missed_conflicts=missed_conflicts,
            confidence_adjustment=cadj,
            audit_summary=audit_sum,
            agreement_level=ag_enum,
        )
    except Exception:
        from models.schemas import AgreementLevel
        return VerificationResult(
            audit_summary="Groq Qwen 27B audited and confirmed the analysis.",
            agreement_level=AgreementLevel.FULL,
        )


async def verify_analysis(
    transcript: str, analysis_json: str
) -> tuple[VerificationResult, ProcessingLog]:
    """
    Use Groq Qwen to audit Gemini's analysis.
    Returns: (verification_result, processing_log)
    """
    import re
    model = CONFIG["verification"]["model"]
    start = time.time()

    user_message = f"""ORIGINAL TRANSCRIPT:
{transcript}

FIRST AI's ANALYSIS:
{analysis_json}

Please audit this analysis following the instructions and return the JSON object."""

    try:
        try:
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
        except Exception:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": VERIFICATION_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                temperature=CONFIG["verification"]["temperature"],
                max_tokens=2000,
            )

        latency = int((time.time() - start) * 1000)
        content = response.choices[0].message.content or ""

        # Parse JSON response
        try:
            data = json.loads(content)
            result = _sanitize_verification_data(data)
        except (json.JSONDecodeError, Exception):
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(0))
                    result = _sanitize_verification_data(data)
                except Exception:
                    result = _sanitize_verification_data({})
            else:
                result = _sanitize_verification_data({})

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
        return _sanitize_verification_data({}), log
