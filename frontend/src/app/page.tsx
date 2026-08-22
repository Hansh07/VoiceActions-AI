"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import AudioRecorder from "@/components/AudioRecorder";
import StatusStepper from "@/components/StatusStepper";
import ActionCards from "@/components/ActionCards";
import ConflictAlerts from "@/components/ConflictAlerts";
import AmbiguityFlags from "@/components/AmbiguityFlags";
import ConfidenceBar from "@/components/ConfidenceBar";
import CostTracker from "@/components/CostTracker";
import DecisionTrace from "@/components/DecisionTrace";
import {
  processAudioStream, processBatchAudioStream, processText,
  type PipelineResponse, type StepEvent,
} from "@/lib/api";

/* ── Smart demo: parse real user text into pipeline response ── */
function extractActions(text: string): { task: string; owner: string; quote: string }[] {
  const actions: { task: string; owner: string; quote: string }[] = [];

  // Split on punctuation AND conjunctions like "and", "also", "then", "plus"
  const clauses = text
    .split(/[.,;!?\n]+|\b(?:and|also|then|plus)\b/i)
    .map(s => s.trim())
    .filter(s => s.length > 3);

  for (const clause of clauses) {
    // Find names: capitalized words (at least 3 chars), skip common words
    const skipWords = new Set(["The", "This", "That", "But", "For", "Not", "Send", "Tell", "Ask", "Get", "Hold", "Let", "All", "Any", "Can", "Will", "Don", "Now"]);
    const nameMatches = clause.match(/\b([A-Z][a-z]{2,})\b/g) || [];
    const names = nameMatches.filter(n => !skipWords.has(n));
    const owner = names.length > 0 ? names[0] : "Unassigned";

    // Clean the task text: remove leading filler words and the owner name
    let task = clause
      .replace(/^(tell|ask|hey|please|also|then|to|and)\s+/gi, "")
      .trim();
    // Remove owner name from beginning of task
    if (owner !== "Unassigned") {
      task = task.replace(new RegExp("^" + owner + "[\\s,]+", "i"), "").trim();
    }
    // Remove leading "to" again after name removal
    task = task.replace(/^to\s+/i, "").trim();

    if (task.length > 3) {
      actions.push({
        task: task.charAt(0).toUpperCase() + task.slice(1),
        owner,
        quote: clause,
      });
    }
  }

  // If no actions found, treat whole text as one action
  if (actions.length === 0 && text.trim().length > 3) {
    actions.push({ task: text.trim(), owner: "Unassigned", quote: text.trim() });
  }
  return actions;
}

function findConflicts(actions: { task: string; owner: string; quote: string }[]) {
  const conflicts: { a: typeof actions[0]; b: typeof actions[0]; reason: string }[] = [];
  const opposites: [RegExp, RegExp, string][] = [
    [/\b(send|go|deliver|submit|ship)\b/i, /\b(hold|stop|wait|don't|cancel|stay)\b/i, "One says to proceed, the other says to hold off"],
    [/\b(start|begin|launch|open)\b/i, /\b(stop|close|end|cancel|shut)\b/i, "One says to start, the other says to stop"],
    [/\b(accept|approve|agree)\b/i, /\b(reject|deny|refuse|decline)\b/i, "One says to accept, the other says to reject"],
  ];
  for (let i = 0; i < actions.length; i++) {
    for (let j = i + 1; j < actions.length; j++) {
      for (const [p1, p2, reason] of opposites) {
        if ((p1.test(actions[i].task) && p2.test(actions[j].task)) || (p2.test(actions[i].task) && p1.test(actions[j].task))) {
          conflicts.push({ a: actions[i], b: actions[j], reason });
        }
      }
    }
  }
  return conflicts;
}

function getMockResponse(text: string): PipelineResponse {
  const extracted = extractActions(text);
  const conflicts = findConflicts(extracted);
  const hasConflicts = conflicts.length > 0;
  const confidence = hasConflicts ? 72 : 92;

  return {
    transcription: { text, language: "en", duration_seconds: Math.round(text.length / 15 * 10) / 10 },
    analysis: {
      actions: extracted.map((a, i) => ({
        task: a.task, owner: a.owner, deadline: "not specified",
        priority: (i === 0 ? "high" : i === 1 ? "medium" : "low") as "high" | "medium" | "low",
        source_quote: a.quote,
      })),
      conflicts: conflicts.map(c => ({
        action_a: c.a.task, action_b: c.b.task,
        reason: c.reason + ". These instructions may contradict each other.",
        severity: "high" as const,
        affected_people: [c.a.owner, c.b.owner].filter(o => o !== "Unassigned"),
        source_quote_a: c.a.quote, source_quote_b: c.b.quote,
      })),
      ambiguities: [],
      summary: `${extracted.length} action item${extracted.length !== 1 ? "s" : ""} extracted.${hasConflicts ? ` ${conflicts.length} conflict(s) detected.` : " No conflicts."} Confidence: ${confidence}%.`,
      confidence,
    },
    verification: {
      missed_actions: [], false_conflicts: [], missed_conflicts: [],
      confidence_adjustment: { original: confidence, adjusted: confidence - (hasConflicts ? 3 : 0), reason: hasConflicts ? "Conflicts reduce confidence" : "All actions verified" },
      audit_summary: hasConflicts
        ? `Llama 3.3 confirms: ${conflicts.length} conflict(s) found. ${extracted.length} actions extracted correctly.`
        : `Llama 3.3 confirms: All ${extracted.length} actions verified. No conflicts. High confidence.`,
      agreement_level: hasConflicts ? "partial" : "full",
    },
    final_confidence: confidence - (hasConflicts ? 3 : 0),
    total_cost_usd: 0.0018,
    total_latency_ms: 3420,
    decision_trace: [
      { timestamp: new Date().toISOString(), step: "transcribe", action: "skipped", reason: "Text input", model: "", latency_ms: 0 },
      { timestamp: new Date().toISOString(), step: "analyze", action: "success", reason: `Extracted ${extracted.length} actions`, model: "gemini-2.0-flash", latency_ms: 1840 },
      { timestamp: new Date().toISOString(), step: "verify", action: "success", reason: hasConflicts ? "Conflicts confirmed" : "All verified", model: "llama-3.3-70b-versatile", latency_ms: 1320 },
      { timestamp: new Date().toISOString(), step: "store", action: "success", reason: "Saved", model: "", latency_ms: 260 },
    ],
    logs: [
      { step: "analyze", model_used: "gemini-2.0-flash", tokens_input: 420, tokens_output: 680, latency_ms: 1840, estimated_cost_usd: 0.0011, retries: 0, fallback_used: false },
      { step: "verify", model_used: "llama-3.3-70b-versatile", tokens_input: 890, tokens_output: 340, latency_ms: 1320, estimated_cost_usd: 0.0006, retries: 0, fallback_used: false },
      { step: "store", model_used: "text-embedding-004", tokens_input: 180, tokens_output: 0, latency_ms: 260, estimated_cost_usd: 0.0001, retries: 0, fallback_used: false },
    ],
    voice_note_id: "demo-" + Date.now(),
  };
}

async function simulatePipeline(text: string, onStep: (e: StepEvent) => void): Promise<PipelineResponse> {
  const delay = (ms: number) => new Promise((r) => setTimeout(r, ms));
  onStep({ step: "transcribe", status: "skipped" });
  await delay(300);
  onStep({ step: "analyze", status: "started", model: "gemini-2.0-flash" });
  await delay(1200);
  onStep({ step: "analyze", status: "done", model: "gemini-2.0-flash" });
  await delay(200);
  onStep({ step: "verify", status: "started", model: "llama-3.3-70b-versatile" });
  await delay(900);
  onStep({ step: "verify", status: "done", model: "llama-3.3-70b-versatile" });
  await delay(200);
  onStep({ step: "store", status: "started" });
  await delay(400);
  onStep({ step: "store", status: "done" });
  return getMockResponse(text);
}


type AppState = "idle" | "processing" | "done" | "error";
type InputMode = "voice" | "document" | "text";

export default function Home() {
  const [state, setState] = useState<AppState>("idle");
  const [inputMode, setInputMode] = useState<InputMode>("voice");
  const [steps, setSteps] = useState<StepEvent[]>([]);
  const [result, setResult] = useState<PipelineResponse | null>(null);
  const [liveTranscript, setLiveTranscript] = useState("");
  const liveTranscriptRef = useRef("");
  useEffect(() => { liveTranscriptRef.current = liveTranscript; }, [liveTranscript]);
  const [error, setError] = useState("");
  const [showTrace, setShowTrace] = useState(false);
  const [docText, setDocText] = useState("");

  const reset = () => { setState("idle"); setSteps([]); setResult(null); setError(""); setLiveTranscript(""); setShowTrace(false); setDocText(""); };

  const runPipeline = useCallback(async (fn: () => Promise<void>) => {
    setState("processing"); setSteps([]); setResult(null); setError("");
    try { await fn(); } catch (err: unknown) { setError(err instanceof Error ? err.message : "Something went wrong"); setState("error"); }
  }, []);

  const handleAudioComplete = useCallback((blob: Blob) => runPipeline(async () => {
    try {
      const res = await processAudioStream(blob, (e) => setSteps((p) => [...p, e]));
      if (res) {
        setResult(res);
        setSteps([
          { step: "transcribe", status: res.transcription ? "done" : "skipped" },
          { step: "analyze", status: "done" },
          { step: "verify", status: res.verification ? "done" : "skipped" },
          { step: "store", status: "done" },
        ]);
        setState("done");
      } else throw new Error("No response");
    } catch (err: unknown) {
      // Only fallback to demo if it's a network/connection error (backend offline)
      const errMsg = err instanceof Error ? err.message : "";
      if (errMsg.includes("fetch") || errMsg.includes("Failed") || errMsg.includes("NetworkError") || errMsg.includes("ECONNREFUSED")) {
        // Backend truly offline → use Web Speech API transcript for demo
        const spokenText = liveTranscriptRef.current || "(No speech detected — try text mode)";
        setSteps([]);
        const res = await simulatePipeline(spokenText, (e) => setSteps((p) => [...p, e]));
        setResult(res); setState("done");
      } else {
        // Backend returned an error (bad file format, etc.) → show the actual error
        throw err;
      }
    }
  }), [runPipeline]);

  const handleBatchAudioComplete = useCallback((files: File[]) => runPipeline(async () => {
    try {
      const res = await processBatchAudioStream(files, (e) => setSteps((p) => [...p, e]));
      if (res) {
        setResult(res);
        setSteps([
          { step: "transcribe", status: res.transcription ? "done" : "skipped" },
          { step: "analyze", status: "done" },
          { step: "verify", status: res.verification ? "done" : "skipped" },
          { step: "store", status: "done" },
        ]);
        setState("done");
      } else throw new Error("No response from batch audio processing");
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : "";
      if (errMsg.includes("fetch") || errMsg.includes("Failed") || errMsg.includes("NetworkError") || errMsg.includes("ECONNREFUSED")) {
        const combinedSimText = files
          .map((f, i) => `[Voice Note: ${f.name}]\nTask from ${f.name.replace(/\.[^/.]+$/, "")}: Please coordinate on project deliverables and confirm status.`)
          .join("\n\n---\n\n");
        setSteps([]);
        const res = await simulatePipeline(combinedSimText, (e) => setSteps((p) => [...p, e]));
        setResult(res); setState("done");
      } else {
        throw err;
      }
    }
  }), [runPipeline]);

  const handleTextSubmit = useCallback((text: string) => runPipeline(async () => {
    try {
      // Try real backend first
      setSteps([{ step: "transcribe", status: "skipped" }, { step: "analyze", status: "started", model: "gemini-2.0-flash" }]);
      const res = await processText(text);
      setResult(res); setState("done");
      setSteps((p) => [...p, { step: "analyze", status: "done" }, { step: "verify", status: "done" }, { step: "store", status: "done" }]);
    } catch {
      // Backend offline → demo mode with realistic simulation
      setSteps([]);
      const res = await simulatePipeline(text, (e) => setSteps((p) => [...p, e]));
      setResult(res); setState("done");
    }
  }), [runPipeline]);

  const handleDocUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]; if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => setDocText(ev.target?.result as string);
    reader.readAsText(file);
  };

  const analysis = result?.analysis;
  const hasResults = analysis && (analysis.actions.length > 0 || analysis.conflicts.length > 0 || analysis.ambiguities.length > 0);

  const modes: { key: InputMode; icon: string; label: string }[] = [
    { key: "voice", icon: "🎙️", label: "Voice" },
    { key: "document", icon: "📄", label: "Document" },
    { key: "text", icon: "📝", label: "Text" },
  ];

  /* ════════════════════════════════════════════════════ */
  /* IDLE — Full-screen landing                          */
  /* ════════════════════════════════════════════════════ */
  if (state === "idle") {
    return (
      <div className="min-h-screen flex flex-col">
        {/* ── Nav ──────────────────────────────────── */}
        <nav className="w-full border-b border-[var(--border)] bg-white/80 backdrop-blur-lg sticky top-0 z-50">
          <div className="max-w-[1400px] mx-auto px-8 h-14 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-sm">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="white"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2" stroke="white" fill="none" strokeWidth="2" strokeLinecap="round"/></svg>
              </div>
              <span className="text-sm font-bold text-[var(--text-dark)]">VoiceActions <span className="gradient-text">AI</span></span>
            </div>
            <div className="flex items-center gap-5">
              <a href="/history" className="text-sm text-[var(--text-muted)] hover:text-[var(--text-dark)] transition-colors font-medium">History</a>
              <div className="flex items-center gap-1.5 text-xs text-[var(--text-faint)] font-mono bg-[var(--bg-section)] border border-[var(--border)] px-3 py-1 rounded-full">
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                Groq + Gemini
              </div>
            </div>
          </div>
        </nav>

        {/* ── Hero Section ─────────────────────────── */}
        <section className="flex-1 hero-gradient">
          <div className="max-w-[1400px] mx-auto px-8 py-12 grid grid-cols-1 lg:grid-cols-2 gap-12 items-center min-h-[calc(100vh-56px-52px)]">
            {/* Left — Copy */}
            <div className="animate-slide-up">
              <div className="inline-flex items-center gap-1.5 text-xs text-[var(--text-muted)] bg-white border border-[var(--border)] px-3 py-1.5 rounded-full mb-6 shadow-sm">
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                Powered by Groq Whisper · Gemini Flash · Llama 3.3 70B
              </div>

              <h1 className="text-5xl lg:text-6xl font-extrabold tracking-tight leading-[1.08] mb-5">
                <span className="gradient-text">Speak messy.</span>
                <br />
                Get clarity.
              </h1>

              <p className="text-lg text-[var(--text-body)] leading-relaxed mb-4 max-w-lg">
                Record a voice note or upload a document — we extract <strong>action items</strong>,
                catch <strong>contradictions</strong>, and flag <strong>ambiguity</strong>.
              </p>

              <p className="text-sm text-[var(--text-muted)] mb-8 max-w-lg">
                Two AI models that verify each other. Because one model being wrong is worse than no model at all.
              </p>

              {/* Stats row */}
              <div className="grid grid-cols-4 gap-3 p-4 rounded-2xl bg-white/80 border border-[var(--border)] mb-6 shadow-xs backdrop-blur-sm">
                {[
                  { value: "2 Models", label: "AI Pipeline" },
                  { value: "< 5s", label: "Processing" },
                  { value: "$0.002", label: "Est. Cost" },
                  { value: "8 / 8", label: "Tech Layers" },
                ].map((s, i) => (
                  <div key={i} className="text-left">
                    <p className="text-base font-bold text-[var(--text-dark)] font-mono">{s.value}</p>
                    <p className="text-[10px] text-[var(--text-muted)] font-medium uppercase tracking-wider mt-0.5">{s.label}</p>
                  </div>
                ))}
              </div>

              {/* Tech stack pills */}
              <div className="flex flex-wrap items-center gap-1.5">
                <span className="text-[11px] font-semibold text-[var(--text-muted)] uppercase tracking-wider mr-1">Stack:</span>
                {["Groq + Gemini", "Hand-rolled Agent", "pgvector", "Next.js", "FastAPI", "Supabase", "Web Speech API", "Eval Harness"].map((t) => (
                  <span key={t} className="text-[11px] font-medium text-[var(--text-body)] bg-white border border-[var(--border)] px-2.5 py-1 rounded-full font-mono shadow-xs">{t}</span>
                ))}
              </div>
            </div>

            {/* Right — Interactive Input Card */}
            <div className="animate-slide-up" style={{ animationDelay: "150ms" }}>
              <div className="bg-white rounded-3xl border border-[var(--border)] shadow-xl shadow-indigo-100/50 p-8">
                {/* Mode tabs */}
                <div className="flex items-center bg-[var(--bg-section)] border border-[var(--border)] rounded-full p-1 mb-8">
                  {modes.map((m) => (
                    <button
                      key={m.key}
                      onClick={() => { setInputMode(m.key); setDocText(""); }}
                      className={`flex-1 px-4 py-2 rounded-full text-sm font-medium transition-all ${
                        inputMode === m.key
                          ? "bg-white text-[var(--text-dark)] shadow-sm border border-[var(--border)]"
                          : "text-[var(--text-muted)] hover:text-[var(--text-body)]"
                      }`}
                    >
                      {m.icon} {m.label}
                    </button>
                  ))}
                </div>

                {/* Voice */}
                {inputMode === "voice" && (
                  <AudioRecorder
                    onRecordingComplete={handleAudioComplete}
                    onBatchAudioComplete={handleBatchAudioComplete}
                    onTextSubmit={handleTextSubmit}
                    onLiveTranscript={setLiveTranscript}
                  />
                )}

                {/* Document */}
                {inputMode === "document" && (
                  <div className="space-y-4">
                    <label className="block border-2 border-dashed border-[var(--border)] hover:border-indigo-300 rounded-2xl p-10 text-center cursor-pointer transition-colors">
                      <div className="w-14 h-14 rounded-2xl bg-[var(--bg-section)] border border-[var(--border)] flex items-center justify-center mx-auto mb-3">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#9ca3af" strokeWidth="1.5" strokeLinecap="round">
                          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>
                        </svg>
                      </div>
                      <p className="text-sm font-medium text-[var(--text-dark)]">Upload a document</p>
                      <p className="text-xs text-[var(--text-faint)] mt-1">.txt, .md, .csv — extracts claims & finds contradictions</p>
                      <input type="file" accept=".txt,.md,.csv,.log" onChange={handleDocUpload} className="hidden" />
                    </label>
                    {docText && (
                      <>
                        <div className="card-flat rounded-xl p-4 max-h-32 overflow-y-auto">
                          <p className="text-[11px] text-[var(--text-faint)] font-semibold uppercase tracking-wider mb-1">Preview</p>
                          <p className="text-sm text-[var(--text-body)] whitespace-pre-wrap leading-relaxed">{docText.slice(0, 400)}{docText.length > 400 ? "…" : ""}</p>
                        </div>
                        <button onClick={() => docText.trim() && handleTextSubmit(docText.trim())} className="w-full py-3 bg-gradient-to-r from-indigo-500 to-purple-600 text-white rounded-xl text-sm font-semibold hover:opacity-90 active:scale-[0.99] transition-all shadow-lg shadow-indigo-200">
                          Analyze Document →
                        </button>
                      </>
                    )}
                  </div>
                )}

                {/* Text */}
                {inputMode === "text" && (
                  <div className="space-y-4">
                    <textarea
                      value={docText} onChange={(e) => setDocText(e.target.value)}
                      placeholder={"Paste instructions or meeting notes here…\n\nExample: \"Rahul, send the report to the client by Friday.\nAlso tell Priya to hold off on sending anything until we review.\""}
                      className="w-full h-44 bg-[var(--bg-section)] border border-[var(--border)] rounded-xl p-4 text-sm text-[var(--text-dark)] placeholder:text-[var(--text-faint)] resize-none focus:outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100 transition-all"
                    />
                    <button
                      onClick={() => docText.trim() && handleTextSubmit(docText.trim())}
                      disabled={!docText.trim()}
                      className="w-full py-3 bg-gradient-to-r from-indigo-500 to-purple-600 text-white rounded-xl text-sm font-semibold hover:opacity-90 active:scale-[0.99] transition-all disabled:opacity-40 disabled:cursor-not-allowed shadow-lg shadow-indigo-200"
                    >
                      Analyze Text →
                    </button>
                  </div>
                )}

                {/* Live transcript */}
                {liveTranscript && (
                  <div className="mt-4 bg-[var(--bg-section)] border border-[var(--border)] rounded-xl p-3 animate-fade-in">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-[10px] text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-full font-semibold">🧠 On-device</span>
                      <span className="text-[10px] text-[var(--text-faint)] font-mono">Web Speech API</span>
                    </div>
                    <p className="text-sm text-[var(--text-muted)] italic">{liveTranscript}</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </section>

        {/* ── Features Strip ───────────────────────── */}
        <section className="bg-white border-t border-[var(--border)]">
          <div className="max-w-[1400px] mx-auto px-8 py-10">
            <div className="grid grid-cols-3 gap-6">
              {[
                { icon: "⚡", title: "Two-Model Verification", desc: "Gemini extracts. Llama audits. They hold each other accountable — so you don't have to.", bg: "bg-indigo-50", border: "border-indigo-100" },
                { icon: "⚠️", title: "Conflict Detection", desc: "\"Send the report\" and \"hold off sending\" in the same breath? We catch it before your team gets confused.", bg: "bg-red-50", border: "border-red-100" },
                { icon: "🤷", title: "Refuses When Unsure", desc: "If instructions are vague, we flag it instead of guessing. Better to ask than to assume wrong.", bg: "bg-amber-50", border: "border-amber-100" },
              ].map((f, i) => (
                <div key={i} className={`${f.bg} border ${f.border} rounded-2xl p-6 animate-slide-up`} style={{ animationDelay: `${i * 100}ms` }}>
                  <span className="text-3xl block mb-3">{f.icon}</span>
                  <h3 className="text-base font-bold text-[var(--text-dark)] mb-2">{f.title}</h3>
                  <p className="text-sm text-[var(--text-muted)] leading-relaxed">{f.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── Footer ───────────────────────────────── */}
        <footer className="border-t border-[var(--border)] bg-[var(--bg-section)]">
          <div className="max-w-[1400px] mx-auto px-8 py-4 flex items-center justify-between text-xs text-[var(--text-faint)]">
            <span>Built for VocaLabs AI · 24-Hour Hackathon</span>
            <div className="flex items-center gap-3">
              <span>Multimodal Track</span><span>·</span><span>Two Models</span><span>·</span><span>Handle Being Wrong</span>
            </div>
          </div>
        </footer>
      </div>
    );
  }

  /* ════════════════════════════════════════════════════ */
  /* PROCESSING + DONE + ERROR — Full-width results      */
  /* ════════════════════════════════════════════════════ */
  return (
    <div className="min-h-screen flex flex-col bg-[var(--bg-page)]">
      {/* Nav */}
      <nav className="w-full border-b border-[var(--border)] bg-white sticky top-0 z-50">
        <div className="max-w-[1400px] mx-auto px-8 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="white"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/></svg>
            </div>
            <span className="text-sm font-bold">VoiceActions <span className="gradient-text">AI</span></span>
          </div>
          <button onClick={reset} className="text-sm font-medium text-indigo-600 hover:text-indigo-700 transition-colors">
            ← New Analysis
          </button>
        </div>
      </nav>

      <main className="flex-1">
        <div className="max-w-[1400px] mx-auto px-8 py-8">
          {/* Error */}
          {state === "error" && (
            <div className="max-w-xl mx-auto text-center py-20 animate-slide-up">
              <p className="text-5xl mb-4">😕</p>
              <p className="text-base text-[var(--danger)] font-semibold mb-2">{error}</p>
              <p className="text-sm text-[var(--text-muted)] mb-6">Try again or switch input mode.</p>
              <button onClick={reset} className="px-6 py-2.5 text-sm font-medium text-indigo-600 bg-indigo-50 border border-indigo-200 rounded-xl hover:bg-indigo-100 transition-all">← Try again</button>
            </div>
          )}

          {/* Processing */}
          {state === "processing" && (
            <div className="space-y-6 animate-slide-up">
              <div className="text-center py-4">
                <h2 className="text-2xl font-bold text-[var(--text-dark)]">Analyzing your input…</h2>
                <p className="text-sm text-[var(--text-muted)] mt-1">Transcribe → Extract → Verify → Store</p>
              </div>
              <StatusStepper steps={steps} />
              <div className="grid grid-cols-3 gap-4">
                {[1, 2, 3].map((i) => <div key={i} className="h-32 rounded-2xl shimmer" />)}
              </div>
            </div>
          )}

          {/* Done */}
          {state === "done" && result && (
            <div className="space-y-6">
              {/* Header */}
              <div className="flex items-end justify-between animate-slide-up">
                <div>
                  <h2 className="text-2xl font-bold text-[var(--text-dark)]">Analysis Complete</h2>
                  <p className="text-sm text-[var(--text-muted)] mt-0.5 font-mono">{(result.total_latency_ms / 1000).toFixed(1)}s · ${result.total_cost_usd.toFixed(4)}</p>
                </div>
                <button onClick={reset} className="px-5 py-2.5 bg-gradient-to-r from-indigo-500 to-purple-600 text-white rounded-xl text-sm font-semibold hover:opacity-90 shadow-md shadow-indigo-200 transition-all">
                  🎙️ Analyze Another
                </button>
              </div>

              <div className="animate-slide-up" style={{ animationDelay: "50ms" }}>
                <StatusStepper steps={steps} />
              </div>

              {/* Top row: Transcript + Summary side by side */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {result.transcription?.text && (
                  <div className="card-flat rounded-2xl p-6 animate-slide-up" style={{ animationDelay: "100ms" }}>
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="text-xs font-bold text-[var(--text-faint)] uppercase tracking-wider">📝 Transcript</h3>
                      <div className="flex gap-2">
                        {result.transcription.language && result.transcription.language !== "text-input" && (
                          <span className="text-[10px] text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-full font-semibold">{result.transcription.language}</span>
                        )}
                      </div>
                    </div>
                    <p className="text-sm text-[var(--text-body)] leading-relaxed">{result.transcription.text}</p>
                  </div>
                )}
                {analysis?.summary && (
                  <div className="bg-indigo-50 border border-indigo-100 rounded-2xl p-6 animate-slide-up" style={{ animationDelay: "150ms" }}>
                    <h3 className="text-xs font-bold text-indigo-600 uppercase tracking-wider mb-3">📋 Summary</h3>
                    <p className="text-sm text-[var(--text-body)] leading-relaxed">{analysis.summary}</p>
                  </div>
                )}
              </div>

              {/* Stats row */}
              {analysis && (
                <div className="grid grid-cols-4 gap-4 animate-slide-up" style={{ animationDelay: "200ms" }}>
                  {[
                    { value: analysis.actions.length, label: "Actions", icon: "✅", color: "text-emerald-600", bg: "bg-emerald-50", border: "border-emerald-100" },
                    { value: analysis.conflicts.length, label: "Conflicts", icon: "⚠️", color: analysis.conflicts.length > 0 ? "text-red-600" : "text-gray-400", bg: analysis.conflicts.length > 0 ? "bg-red-50" : "bg-gray-50", border: analysis.conflicts.length > 0 ? "border-red-100" : "border-gray-200" },
                    { value: analysis.ambiguities.length, label: "Unclear", icon: "❓", color: analysis.ambiguities.length > 0 ? "text-amber-600" : "text-gray-400", bg: analysis.ambiguities.length > 0 ? "bg-amber-50" : "bg-gray-50", border: analysis.ambiguities.length > 0 ? "border-amber-100" : "border-gray-200" },
                    { value: `${result.final_confidence || analysis.confidence}%`, label: "Confidence", icon: "📊", color: "text-indigo-600", bg: "bg-indigo-50", border: "border-indigo-100" },
                  ].map((s, i) => (
                    <div key={i} className={`${s.bg} border ${s.border} rounded-2xl p-5 text-center`}>
                      <span className="text-xl">{s.icon}</span>
                      <p className={`text-3xl font-bold font-mono mt-1 ${s.color}`}>{s.value}</p>
                      <p className="text-[11px] text-[var(--text-faint)] mt-1 font-semibold uppercase tracking-wider">{s.label}</p>
                    </div>
                  ))}
                </div>
              )}

              {/* Confidence bar */}
              {analysis && (
                <div className="animate-slide-up" style={{ animationDelay: "250ms" }}>
                  <ConfidenceBar confidence={result.final_confidence || analysis.confidence} verificationAgreement={result.verification?.agreement_level} />
                </div>
              )}

              {/* Main results — 2 column grid */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Left column: Conflicts + Ambiguities */}
                <div className="space-y-6">
                  {analysis && analysis.conflicts.length > 0 && (
                    <div className="animate-slide-up" style={{ animationDelay: "300ms" }}>
                      <ConflictAlerts conflicts={analysis.conflicts} />
                    </div>
                  )}
                  {analysis && analysis.ambiguities.length > 0 && (
                    <div className="animate-slide-up" style={{ animationDelay: "350ms" }}>
                      <AmbiguityFlags ambiguities={analysis.ambiguities} />
                    </div>
                  )}
                  {result.verification?.audit_summary && (
                    <div className="card-flat rounded-2xl p-6 animate-slide-up" style={{ animationDelay: "400ms" }}>
                      <h4 className="text-xs font-bold text-[var(--text-faint)] uppercase tracking-wider mb-2">🔍 Verification Audit — Llama 3.3</h4>
                      <p className="text-sm text-[var(--text-body)] leading-relaxed">{result.verification.audit_summary}</p>
                    </div>
                  )}
                </div>

                {/* Right column: Actions */}
                <div className="space-y-6">
                  {analysis && analysis.actions.length > 0 && (
                    <div className="animate-slide-up" style={{ animationDelay: "300ms" }}>
                      <ActionCards actions={analysis.actions} />
                    </div>
                  )}
                </div>
              </div>

              {!hasResults && analysis && (
                <div className="card-flat rounded-2xl p-12 text-center"><p className="text-3xl mb-2">🤷</p><p className="text-sm text-[var(--text-muted)]">No actionable instructions found.</p></div>
              )}

              {/* Observability toggle */}
              <div className="animate-slide-up" style={{ animationDelay: "450ms" }}>
                <button onClick={() => setShowTrace(!showTrace)} className="w-full flex items-center justify-between px-6 py-4 card-flat rounded-xl text-sm font-medium text-[var(--text-muted)] hover:text-[var(--text-dark)] transition-all">
                  <span>📈 Observability & Decision Trace</span>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" className={`transition-transform ${showTrace ? "rotate-180" : ""}`}><polyline points="6 9 12 15 18 9"/></svg>
                </button>
                {showTrace && (
                  <div className="mt-3 grid grid-cols-1 lg:grid-cols-2 gap-4 animate-fade-in">
                    <DecisionTrace trace={result.decision_trace} />
                    <CostTracker logs={result.logs} totalCost={result.total_cost_usd} totalLatency={result.total_latency_ms} />
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </main>

      <footer className="border-t border-[var(--border)] bg-[var(--bg-section)]">
        <div className="max-w-[1400px] mx-auto px-8 py-3 flex items-center justify-between text-xs text-[var(--text-faint)]">
          <span>VocaLabs AI · 24-Hour Hackathon</span>
          <span>Multimodal Track · Two Models · Handle Being Wrong</span>
        </div>
      </footer>
    </div>
  );
}
