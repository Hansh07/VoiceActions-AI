"""
VoiceActions AI — Embedding Service
Generates embeddings via Gemini for pgvector semantic search.
"""

import time
import google.generativeai as genai
from config import GEMINI_API_KEY, CONFIG

genai.configure(api_key=GEMINI_API_KEY)


async def generate_embedding(text: str) -> list[float]:
    """Generate a single embedding vector for a text."""
    try:
        model = CONFIG["embedding"]["model"]
        result = genai.embed_content(
            model=f"models/{model}",
            content=text,
            task_type="retrieval_document",
        )
        return result["embedding"]
    except Exception as e:
        print(f"[Embedding] Failed: {e}")
        return []


async def generate_query_embedding(text: str) -> list[float]:
    """Generate embedding for a search query."""
    try:
        model = CONFIG["embedding"]["model"]
        result = genai.embed_content(
            model=f"models/{model}",
            content=text,
            task_type="retrieval_query",
        )
        return result["embedding"]
    except Exception as e:
        print(f"[Embedding] Query embedding failed: {e}")
        return []


import asyncio


async def generate_batch_embeddings(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for multiple texts concurrently."""
    if not texts:
        return []
    try:
        tasks = [generate_embedding(text) for text in texts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r if isinstance(r, list) else [] for r in results]
    except Exception as e:
        print(f"[Embedding] Batch failed: {e}")
        return [[] for _ in texts]
