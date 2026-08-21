"""
VoiceActions AI — Pydantic Schemas
All data models for type safety and API validation.
"""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class Priority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Severity(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AgreementLevel(str, Enum):
    FULL = "full"
    PARTIAL = "partial"
    SIGNIFICANT_DISAGREEMENT = "significant_disagreement"


# ─── Action Item ─────────────────────────────────────────
class ActionItem(BaseModel):
    task: str
    owner: str = "unassigned"
    deadline: str = "not specified"
    priority: Priority = Priority.MEDIUM
    source_quote: str = ""


# ─── Conflict ────────────────────────────────────────────
class Conflict(BaseModel):
    action_a: str
    action_b: str
    reason: str
    severity: Severity = Severity.MEDIUM
    affected_people: list[str] = []
    source_quote_a: str = ""
    source_quote_b: str = ""


# ─── Ambiguity ───────────────────────────────────────────
class Ambiguity(BaseModel):
    quote: str
    what_is_unclear: str
    suggestion: str = ""


# ─── Analysis Result (from Gemini) ───────────────────────
class AnalysisResult(BaseModel):
    actions: list[ActionItem] = []
    conflicts: list[Conflict] = []
    ambiguities: list[Ambiguity] = []
    summary: str = ""
    confidence: int = Field(default=0, ge=0, le=100)


# ─── Missed Action (from verification) ──────────────────
class MissedAction(BaseModel):
    task: str
    owner: str = "unassigned"
    source_quote: str = ""


# ─── False Conflict (from verification) ─────────────────
class FalseConflict(BaseModel):
    original_conflict: str
    why_not_conflict: str


# ─── Missed Conflict (from verification) ────────────────
class MissedConflict(BaseModel):
    action_a: str
    action_b: str
    reason: str


# ─── Confidence Adjustment ──────────────────────────────
class ConfidenceAdjustment(BaseModel):
    original: int = 0
    adjusted: int = 0
    reason: str = ""


# ─── Verification Result (from Groq Llama) ──────────────
class VerificationResult(BaseModel):
    missed_actions: list[MissedAction] = []
    false_conflicts: list[FalseConflict] = []
    missed_conflicts: list[MissedConflict] = []
    confidence_adjustment: ConfidenceAdjustment = ConfidenceAdjustment()
    audit_summary: str = ""
    agreement_level: AgreementLevel = AgreementLevel.FULL


# ─── Transcription Result ────────────────────────────────
class TranscriptionResult(BaseModel):
    text: str
    language: str = "unknown"
    duration_seconds: float = 0.0
    segments: list[dict] = []


# ─── Processing Log Entry ────────────────────────────────
class ProcessingLog(BaseModel):
    step: str
    model_used: str
    tokens_input: int = 0
    tokens_output: int = 0
    latency_ms: int = 0
    estimated_cost_usd: float = 0.0
    prompt_version: str = ""
    retries: int = 0
    fallback_used: bool = False
    error: Optional[str] = None


# ─── Decision Trace Entry ────────────────────────────────
class DecisionEntry(BaseModel):
    timestamp: str
    step: str
    action: str  # "started", "retry", "fallback", "success", "failed", "skipped"
    reason: str = ""
    model: str = ""
    latency_ms: int = 0


# ─── Pipeline Step Status (streamed to frontend) ────────
class StepStatus(BaseModel):
    step: str
    status: str  # "started", "done", "error", "skipped"
    data: Optional[dict] = None
    decision_trace: list[DecisionEntry] = []
    log: Optional[ProcessingLog] = None


# ─── Final Pipeline Response ─────────────────────────────
class PipelineResponse(BaseModel):
    transcription: Optional[TranscriptionResult] = None
    analysis: Optional[AnalysisResult] = None
    verification: Optional[VerificationResult] = None
    final_confidence: int = 0
    total_cost_usd: float = 0.0
    total_latency_ms: int = 0
    decision_trace: list[DecisionEntry] = []
    logs: list[ProcessingLog] = []
    voice_note_id: Optional[str] = None


# ─── Search Request ──────────────────────────────────────
class SearchRequest(BaseModel):
    query: str
    limit: int = 10


# ─── Search Result ───────────────────────────────────────
class SearchResult(BaseModel):
    id: str
    task: str
    owner: str
    similarity: float
    voice_note_id: Optional[str] = None
    created_at: Optional[str] = None
