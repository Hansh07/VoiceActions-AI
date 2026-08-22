"use client";

interface StatusStepperProps {
  steps: { step: string; status: string; model?: string; latency_ms?: number; fallback?: boolean }[];
}

const META: Record<string, { label: string; icon: string }> = {
  transcribe: { label: "Transcribe", icon: "🎙️" },
  analyze: { label: "Analyze", icon: "🧠" },
  verify: { label: "Verify", icon: "🔍" },
  store: { label: "Store", icon: "💾" },
};

export default function StatusStepper({ steps }: StatusStepperProps) {
  const pipeline = ["transcribe", "analyze", "verify", "store"];
  const getState = (name: string) => {
    const events = steps.filter((s) => s.step === name);
    return events[events.length - 1]?.status || "pending";
  };
  const hasFallback = (name: string) => steps.some((s) => s.step === name && s.fallback);

  return (
    <div className="card-flat rounded-2xl p-4">
      <div className="flex items-center gap-1">
        {pipeline.map((name, i) => {
          const state = getState(name);
          const meta = META[name] || { label: name, icon: "⚙️" };
          const fb = hasFallback(name);
          return (
            <div key={name} className="flex items-center gap-1 flex-1">
              <div className={`flex items-center gap-1.5 px-3 py-2 rounded-xl text-[11px] font-medium w-full justify-center transition-all ${
                state === "done" ? "bg-green-50 text-green-700 border border-green-200"
                : (state === "started" || state === "progress") ? "bg-indigo-50 text-indigo-600 border border-indigo-200"
                : state === "error" ? "bg-red-50 text-red-600 border border-red-200"
                : state === "skipped" ? "bg-gray-50 text-gray-400 border border-gray-200"
                : state === "fallback" ? "bg-amber-50 text-amber-600 border border-amber-200"
                : "bg-gray-50 text-[var(--text-muted)] border border-[var(--border)]"
              }`}>
                <span className="text-xs">{meta.icon}</span>
                <span className="hidden sm:inline">{meta.label}</span>
                {(state === "started" || state === "progress") && <span className="w-3 h-3 border-[1.5px] border-current border-t-transparent rounded-full spinner" />}
                {state === "done" && <span className="text-[10px]">✓</span>}
                {fb && <span className="text-[9px] bg-amber-100 text-amber-700 px-1 rounded font-mono">fb</span>}
              </div>
              {i < pipeline.length - 1 && <div className={`step-connector ${state === "done" ? "done" : ""}`} />}
            </div>
          );
        })}
      </div>
    </div>
  );
}
