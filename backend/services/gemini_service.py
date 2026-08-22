"""
VoiceActions AI — Gemini Service
Handles: Transcript analysis (action extraction + conflict detection)
"""

import time
import json
import asyncio
import google.generativeai as genai
from config import GEMINI_API_KEY, CONFIG
from prompts import ANALYSIS_PROMPT, ANALYSIS_PROMPT_VERSION
from models.schemas import AnalysisResult, ProcessingLog

genai.configure(api_key=GEMINI_API_KEY)


async def analyze_transcript(transcript: str) -> tuple[AnalysisResult, ProcessingLog]:
    """
    Use Gemini Flash to extract actions, conflicts, and ambiguities.
    Returns: (analysis_result, processing_log)
    """
    model_name = CONFIG["analysis"]["primary"]["model"]
    start = time.time()
    retries = 0
    max_retries = CONFIG["analysis"]["max_retries"]

    last_error = None
    while retries <= max_retries:
        try:
            model = genai.GenerativeModel(
                model_name=model_name,
                generation_config=genai.GenerationConfig(
                    temperature=CONFIG["analysis"]["temperature"],
                    response_mime_type="application/json",
                    max_output_tokens=3000,
                ),
                system_instruction=ANALYSIS_PROMPT,
            )

            response = model.generate_content(
                f"TRANSCRIPT:\n{transcript}\n\nExtract all actions, conflicts, and ambiguities."
            )

            latency = int((time.time() - start) * 1000)
            content = response.text

            # Parse JSON response
            try:
                data = json.loads(content)
                if ("confidence" not in data or data["confidence"] == 0) and data.get("actions"):
                    # Default high baseline confidence when actions are clearly extracted
                    data["confidence"] = 85 if not data.get("conflicts") else 75
                result = AnalysisResult(**data)
            except (json.JSONDecodeError, Exception) as parse_err:
                # Try to extract JSON from response
                result = AnalysisResult(
                    summary="Analysis completed but response parsing had issues",
                    confidence=50,
                )

            # Get token counts
            tokens_in = 0
            tokens_out = 0
            if hasattr(response, "usage_metadata"):
                tokens_in = getattr(response.usage_metadata, "prompt_token_count", 0)
                tokens_out = getattr(response.usage_metadata, "candidates_token_count", 0)

            log = ProcessingLog(
                step="analyze",
                model_used=f"gemini/{model_name}",
                tokens_input=tokens_in,
                tokens_output=tokens_out,
                latency_ms=latency,
                retries=retries,
                prompt_version=ANALYSIS_PROMPT_VERSION,
                estimated_cost_usd=(
                    tokens_in * CONFIG["pricing"]["gemini_flash"]["input"]
                    + tokens_out * CONFIG["pricing"]["gemini_flash"]["output"]
                ),
            )

            return result, log

        except Exception as e:
            last_error = str(e)
            retries += 1
            if retries <= max_retries:
                await asyncio.sleep(1 * retries)

    latency = int((time.time() - start) * 1000)
    log = ProcessingLog(
        step="analyze",
        model_used=f"gemini/{model_name}",
        latency_ms=latency,
        retries=retries,
        error=last_error,
    )
    raise Exception(f"Analysis failed after {max_retries} retries: {last_error}")


async def analyze_transcript_fallback(transcript: str) -> tuple[AnalysisResult, ProcessingLog]:
    """
    Fallback: Use Groq Llama if Gemini is down.
    """
    from services.groq_service import client as groq_client

    model = CONFIG["analysis"]["fallback"]["model"]
    start = time.time()

    try:
        response = groq_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": ANALYSIS_PROMPT},
                {"role": "user", "content": f"/no_think\nTRANSCRIPT:\n{transcript}\n\nExtract all actions, conflicts, and ambiguities."},
            ],
            temperature=CONFIG["analysis"]["temperature"],
            response_format={"type": "json_object"},
            max_tokens=3000,
        )

        latency = int((time.time() - start) * 1000)
        content = response.choices[0].message.content

        try:
            data = json.loads(content)
            result = AnalysisResult(**data)
        except (json.JSONDecodeError, Exception):
            result = AnalysisResult(
                summary="Fallback analysis completed",
                confidence=40,
            )

        tokens_in = getattr(response.usage, "prompt_tokens", 0)
        tokens_out = getattr(response.usage, "completion_tokens", 0)

        log = ProcessingLog(
            step="analyze",
            model_used=f"groq/{model}",
            tokens_input=tokens_in,
            tokens_output=tokens_out,
            latency_ms=latency,
            fallback_used=True,
            estimated_cost_usd=(
                tokens_in * CONFIG["pricing"]["groq_llama"]["input"]
                + tokens_out * CONFIG["pricing"]["groq_llama"]["output"]
            ),
        )

        return result, log

    except Exception as e:
        latency = int((time.time() - start) * 1000)
        log = ProcessingLog(
            step="analyze",
            model_used=f"groq/{model}",
            latency_ms=latency,
            fallback_used=True,
            error=str(e),
        )
        raise
