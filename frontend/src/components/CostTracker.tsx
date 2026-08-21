"use client";
import type { ProcessingLog } from "@/lib/api";

interface CostTrackerProps { logs: ProcessingLog[]; totalCost: number; totalLatency: number; }

export default function CostTracker({ logs, totalCost, totalLatency }: CostTrackerProps) {
  const tokensIn = logs.reduce((s, l) => s + l.tokens_input, 0);
  const tokensOut = logs.reduce((s, l) => s + l.tokens_output, 0);

  return (
    <div className="card-flat rounded-2xl p-5">
      <h4 className="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wider mb-4">📈 Observability — Token & Cost Tracking</h4>
      <div className="grid grid-cols-4 gap-3 mb-4">
        {[
          { value: `${(totalLatency / 1000).toFixed(1)}s`, label: "Latency", color: "text-[var(--text-primary)]" },
          { value: `$${totalCost.toFixed(4)}`, label: "Cost", color: "text-green-600" },
          { value: tokensIn.toLocaleString(), label: "Tokens In", color: "text-indigo-600" },
          { value: tokensOut.toLocaleString(), label: "Tokens Out", color: "text-purple-600" },
        ].map((s, i) => (
          <div key={i} className="text-center py-2.5 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border)]">
            <p className={`text-base font-bold font-mono ${s.color}`}>{s.value}</p>
            <p className="text-[10px] text-[var(--text-muted)] mt-0.5 font-medium">{s.label}</p>
          </div>
        ))}
      </div>
      <div className="space-y-1.5">
        {logs.map((log, i) => (
          <div key={i} className="flex items-center justify-between text-[11px] py-2 px-3 rounded-lg bg-[var(--bg-secondary)] hover:bg-gray-100 transition-colors">
            <div className="flex items-center gap-2">
              <span className="capitalize font-medium text-[var(--text-primary)]">{log.step}</span>
              <span className="text-[10px] font-mono text-[var(--text-muted)]">{log.model_used}</span>
              {log.fallback_used && <span className="text-[9px] bg-amber-100 text-amber-700 px-1.5 py-px rounded font-semibold">FALLBACK</span>}
              {log.retries > 0 && <span className="text-[9px] bg-blue-100 text-blue-700 px-1.5 py-px rounded">{log.retries}× retry</span>}
            </div>
            <div className="flex items-center gap-4 font-mono text-[var(--text-muted)]">
              <span>{(log.latency_ms / 1000).toFixed(1)}s</span>
              <span className="text-green-600">${log.estimated_cost_usd.toFixed(5)}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
