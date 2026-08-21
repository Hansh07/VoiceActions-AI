"use client";
import type { DecisionEntry } from "@/lib/api";

interface DecisionTraceProps { trace: DecisionEntry[]; }

const COLORS: Record<string, string> = {
  started: "text-blue-600", success: "text-green-600", failed: "text-red-600",
  fallback: "text-amber-600", retry: "text-amber-600", skipped: "text-gray-400",
};
const ICONS: Record<string, string> = {
  started: "▶", success: "✓", failed: "✗", fallback: "↩", retry: "↻", skipped: "⊘",
};

export default function DecisionTrace({ trace }: DecisionTraceProps) {
  if (!trace.length) return null;
  return (
    <div className="card-flat rounded-2xl p-5">
      <h4 className="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wider mb-3">🔗 Decision Trace — Agent Loop</h4>
      <div className="space-y-px max-h-64 overflow-y-auto pr-1">
        {trace.map((entry, i) => {
          const color = COLORS[entry.action] || "text-gray-400";
          const icon = ICONS[entry.action] || "•";
          return (
            <div key={i} className="flex items-start gap-2.5 text-[11px] py-2 px-2 rounded-lg hover:bg-[var(--bg-secondary)] transition-colors animate-slide-up" style={{ animationDelay: `${i * 30}ms` }}>
              <div className="flex flex-col items-center shrink-0 mt-px">
                <span className={`text-sm leading-none font-mono ${color}`}>{icon}</span>
                {i < trace.length - 1 && <div className="w-px h-5 bg-[var(--border)] mt-1" />}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-semibold text-[var(--text-primary)] capitalize">{entry.step}</span>
                  <span className={`font-medium ${color}`}>{entry.action}</span>
                  {entry.model && <span className="font-mono text-[10px] text-[var(--text-muted)] bg-[var(--bg-secondary)] px-1.5 py-px rounded">{entry.model}</span>}
                  {entry.latency_ms > 0 && <span className="font-mono text-[10px] text-[var(--text-muted)]">{(entry.latency_ms / 1000).toFixed(1)}s</span>}
                </div>
                {entry.reason && <p className="text-[var(--text-muted)] mt-0.5 leading-relaxed">{entry.reason}</p>}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
