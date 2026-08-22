/**
 * VoiceActions AI — API Client
 * Handles communication with the FastAPI backend.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface ActionItem {
  task: string;
  owner: string;
  deadline: string;
  priority: "high" | "medium" | "low";
  source_quote: string;
}

export interface Conflict {
  action_a: string;
  action_b: string;
  reason: string;
  severity: "high" | "medium" | "low";
  affected_people: string[];
  source_quote_a: string;
  source_quote_b: string;
}

export interface Ambiguity {
  quote: string;
  what_is_unclear: string;
  suggestion: string;
}

export interface TranscriptionResult {
  text: string;
  language: string;
  duration_seconds: number;
}

export interface AnalysisResult {
  actions: ActionItem[];
  conflicts: Conflict[];
  ambiguities: Ambiguity[];
  summary: string;
  confidence: number;
}

export interface VerificationResult {
  missed_actions: { task: string; owner: string; source_quote: string }[];
  false_conflicts: { original_conflict: string; why_not_conflict: string }[];
  missed_conflicts: { action_a: string; action_b: string; reason: string }[];
  confidence_adjustment: {
    original: number;
    adjusted: number;
    reason: string;
  };
  audit_summary: string;
  agreement_level: "full" | "partial" | "significant_disagreement";
}

export interface DecisionEntry {
  timestamp: string;
  step: string;
  action: string;
  reason: string;
  model: string;
  latency_ms: number;
}

export interface ProcessingLog {
  step: string;
  model_used: string;
  tokens_input: number;
  tokens_output: number;
  latency_ms: number;
  estimated_cost_usd: number;
  retries: number;
  fallback_used: boolean;
  error?: string;
}

export interface PipelineResponse {
  transcription?: TranscriptionResult;
  analysis?: AnalysisResult;
  verification?: VerificationResult;
  final_confidence: number;
  total_cost_usd: number;
  total_latency_ms: number;
  decision_trace: DecisionEntry[];
  logs: ProcessingLog[];
  voice_note_id?: string;
}

export interface StepEvent {
  step: string;
  status: string;
  data?: any;
  log?: ProcessingLog;
  error?: string;
  model?: string;
  fallback?: boolean;
}

/**
 * Process audio via streaming endpoint.
 * Calls onStep for each pipeline step event.
 */
export async function processAudioStream(
  audioBlob: Blob,
  onStep: (event: StepEvent) => void
): Promise<PipelineResponse | null> {
  const formData = new FormData();
  // Preserve original filename for uploaded files; use "recording.webm" for mic recordings
  const fileName = (audioBlob as File).name || "recording.webm";
  formData.append("audio", audioBlob, fileName);

  try {
    const response = await fetch(`${API_BASE}/api/process`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`API error: ${response.status} — ${error}`);
    }

    const reader = response.body?.getReader();
    if (!reader) throw new Error("No response body");

    const decoder = new TextDecoder();
    let finalResult: PipelineResponse | null = null;
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (!line.trim()) continue;
        try {
          const event = JSON.parse(line);
          if (event.step === "final_result") {
            finalResult = event.data;
          } else {
            onStep(event);
          }
        } catch {
          // Skip malformed lines
        }
      }
    }

    return finalResult;
  } catch (error) {
    console.error("Stream processing failed:", error);
    throw error;
  }
}

/**
 * Process audio via sync endpoint (simpler, for testing).
 */
export async function processAudioSync(
  audioBlob: Blob
): Promise<PipelineResponse> {
  const formData = new FormData();
  const fileName = (audioBlob as File).name || "recording.webm";
  formData.append("audio", audioBlob, fileName);

  const response = await fetch(`${API_BASE}/api/process-sync`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`API error: ${response.status} — ${error}`);
  }

  return response.json();
}

/**
 * Process text directly (graceful degradation when mic fails).
 */
export async function processText(text: string): Promise<PipelineResponse> {
  const response = await fetch(`${API_BASE}/api/process-text`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`API error: ${response.status} — ${error}`);
  }

  return response.json();
}

/**
 * Semantic search over past action items.
 */
export async function searchActions(
  query: string,
  limit: number = 10
): Promise<{ results: any[]; query: string }> {
  const response = await fetch(`${API_BASE}/api/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, limit }),
  });

  if (!response.ok) {
    throw new Error("Search failed");
  }

  return response.json();
}

/**
 * Get history of past voice notes.
 */
export async function getHistory(): Promise<{ voice_notes: any[] }> {
  const response = await fetch(`${API_BASE}/api/history`);
  if (!response.ok) throw new Error("Failed to fetch history");
  return response.json();
}
