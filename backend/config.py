"""
VoiceActions AI — Central Configuration
All model choices, feature flags, and thresholds live here.
This is the curveball-defense file — any judge-mandated change starts here.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load from backend/.env and current working directory .env
backend_env = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=backend_env)
load_dotenv()

# ─── API Keys ────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

if GEMINI_API_KEY:
    os.environ["GOOGLE_API_KEY"] = GEMINI_API_KEY
    os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY

# ─── Model Configuration ─────────────────────────────────
CONFIG = {
    "transcription": {
        "primary": {
            "provider": "groq",
            "model": "whisper-large-v3",
        },
        "fallback": {
            "provider": "gemini",
            "model": "gemini-flash-latest",
        },
        "max_retries": 2,
        "timeout_seconds": 30,
    },
    "analysis": {
        "primary": {
            "provider": "gemini",
            "model": "gemini-flash-lite-latest",
        },
        "fallback": {
            "provider": "groq",
            "model": "qwen/qwen3.6-27b",
        },
        "temperature": 0.2,
        "max_retries": 2,
    },
    "verification": {
        "provider": "groq",
        "model": "qwen/qwen3.6-27b",
        "temperature": 0.1,
        "enabled": True,  # Feature flag — can disable for speed
    },
    "embedding": {
        "provider": "gemini",
        "model": "gemini-embedding-001",
        "dimensions": 3072,
    },
    "features": {
        "conflict_detection": True,
        "ambiguity_detection": True,
        "semantic_search": True,
        "on_device_preview": True,
        "cost_tracking": True,
        "verification_step": True,
        "store_to_database": True,
    },
    # Cost per token (USD) — for observability
    "pricing": {
        "groq_whisper": {"per_second": 0.0001},
        "groq_llama": {"input": 0.00000059, "output": 0.00000079},
        "gemini_flash": {"input": 0.000000075, "output": 0.0000003},
        "gemini_embedding": {"input": 0.00000001},
    },
}
