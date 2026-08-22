"""
VoiceActions AI — Supabase Service
Handles: Database operations + audio file storage
"""

from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY
from models.schemas import ProcessingLog
from typing import Optional
import json


def get_client() -> Optional[Client]:
    """Get Supabase client. Returns None if not configured."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    return create_client(SUPABASE_URL, SUPABASE_KEY)


async def store_voice_note(
    transcript: str,
    language: str = "auto",
    duration_seconds: float = 0.0,
    audio_url: str = "",
) -> Optional[str]:
    """Store a voice note and return its ID."""
    client = get_client()
    if not client:
        return None

    try:
        result = client.table("voice_notes").insert({
            "transcript": transcript,
            "language": language,
            "duration_seconds": duration_seconds,
            "audio_url": audio_url,
        }).execute()

        if result.data:
            return result.data[0]["id"]
        return None
    except Exception as e:
        print(f"[Supabase] Failed to store voice note: {e}")
        return None


async def store_actions(voice_note_id: str, actions: list, embeddings: list[list[float]] = []):
    """Store action items with optional embeddings for pgvector."""
    client = get_client()
    if not client:
        return

    try:
        for i, action in enumerate(actions):
            task = action.task if hasattr(action, "task") else (action.get("task", "") if isinstance(action, dict) else "")
            owner = action.owner if hasattr(action, "owner") else (action.get("owner", "unassigned") if isinstance(action, dict) else "unassigned")
            deadline = action.deadline if hasattr(action, "deadline") else (action.get("deadline", "not specified") if isinstance(action, dict) else "not specified")
            priority = action.priority if hasattr(action, "priority") else (action.get("priority", "medium") if isinstance(action, dict) else "medium")
            if hasattr(priority, "value"):
                priority = priority.value
            source_quote = action.source_quote if hasattr(action, "source_quote") else (action.get("source_quote", "") if isinstance(action, dict) else "")

            row = {
                "voice_note_id": voice_note_id,
                "task": task,
                "owner": owner,
                "deadline": deadline,
                "priority": str(priority),
                "source_quote": source_quote,
            }
            # Add embedding if available
            if i < len(embeddings) and embeddings[i]:
                row["embedding"] = json.dumps(embeddings[i])

            client.table("action_items").insert(row).execute()
    except Exception as e:
        print(f"[Supabase] Failed to store actions: {e}")


async def store_conflicts(voice_note_id: str, conflicts: list):
    """Store detected conflicts."""
    client = get_client()
    if not client:
        return

    try:
        for conflict in conflicts:
            reason = conflict.reason if hasattr(conflict, "reason") else (conflict.get("reason", "") if isinstance(conflict, dict) else "")
            severity = conflict.severity if hasattr(conflict, "severity") else (conflict.get("severity", "medium") if isinstance(conflict, dict) else "medium")
            if hasattr(severity, "value"):
                severity = severity.value
            affected_people = conflict.affected_people if hasattr(conflict, "affected_people") else (conflict.get("affected_people", []) if isinstance(conflict, dict) else [])

            client.table("conflicts").insert({
                "voice_note_id": voice_note_id,
                "reason": reason,
                "severity": str(severity),
                "affected_people": affected_people,
            }).execute()
    except Exception as e:
        print(f"[Supabase] Failed to store conflicts: {e}")


async def store_processing_log(voice_note_id: str, log: ProcessingLog):
    """Store a processing log entry for observability."""
    client = get_client()
    if not client:
        return

    try:
        client.table("processing_logs").insert({
            "voice_note_id": voice_note_id,
            "step": log.step,
            "model_used": log.model_used,
            "tokens_input": log.tokens_input,
            "tokens_output": log.tokens_output,
            "latency_ms": log.latency_ms,
            "estimated_cost_usd": log.estimated_cost_usd,
            "prompt_version": log.prompt_version,
            "retries": log.retries,
            "fallback_used": log.fallback_used,
            "error": log.error,
        }).execute()
    except Exception as e:
        print(f"[Supabase] Failed to store log: {e}")


async def search_actions(query_embedding: list[float], limit: int = 10) -> list[dict]:
    """Semantic search over past action items using pgvector."""
    client = get_client()
    if not client:
        return []

    try:
        result = client.rpc("search_actions", {
            "query_embedding": json.dumps(query_embedding),
            "match_count": limit,
        }).execute()

        return result.data or []
    except Exception as e:
        print(f"[Supabase] Search failed: {e}")
        return []


async def upload_audio(file_path: str, file_name: str) -> str:
    """Upload audio file to Supabase Storage. Returns public URL."""
    client = get_client()
    if not client:
        return ""

    try:
        with open(file_path, "rb") as f:
            client.storage.from_("audio").upload(
                path=file_name,
                file=f,
                file_options={"content-type": "audio/webm"},
            )

        url = client.storage.from_("audio").get_public_url(file_name)
        return url
    except Exception as e:
        print(f"[Supabase] Audio upload failed: {e}")
        return ""


async def get_recent_voice_notes(limit: int = 20) -> list[dict]:
    """Get recent voice notes with their actions."""
    client = get_client()
    if not client:
        return []

    try:
        result = (
            client.table("voice_notes")
            .select("*, action_items(*), conflicts(*)")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []
    except Exception as e:
        print(f"[Supabase] Failed to fetch voice notes: {e}")
        return []
