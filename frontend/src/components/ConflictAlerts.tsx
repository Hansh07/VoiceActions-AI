"use client";
import type { Conflict } from "@/lib/api";

interface ConflictAlertsProps { conflicts: Conflict[]; }

export default function ConflictAlerts({ conflicts }: ConflictAlertsProps) {
  if (!conflicts.length) return null;
  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-red-700 flex items-center gap-2">
        <span className="w-6 h-6 rounded-lg bg-red-50 border border-red-200 flex items-center justify-center text-xs">⚠️</span>
        Conflicts Detected
        <span className="ml-auto text-[11px] font-mono font-normal text-red-500 bg-red-50 border border-red-100 px-2 py-0.5 rounded-full">{conflicts.length} found</span>
      </h3>
      <div className="grid gap-3">
        {conflicts.map((conflict, i) => (
          <div key={i} className={`rounded-2xl p-5 bg-red-50/50 border border-red-200 severity-${conflict.severity} animate-slide-up`} style={{ animationDelay: `${i * 80}ms` }}>
            <div className="flex items-center justify-between mb-4">
              <span className={`text-[10px] px-2.5 py-0.5 rounded-full font-bold uppercase tracking-widest badge-${conflict.severity}`}>{conflict.severity} severity</span>
              {conflict.affected_people.length > 0 && (
                <span className="text-[11px] text-[var(--text-muted)] font-medium">👥 {conflict.affected_people.join(", ")}</span>
              )}
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {[
                { label: "Action A", text: conflict.action_a, quote: conflict.source_quote_a },
                { label: "Action B", text: conflict.action_b, quote: conflict.source_quote_b },
              ].map((side) => (
                <div key={side.label} className="bg-white rounded-xl p-3.5 border border-red-100">
                  <p className="text-[10px] text-red-500 font-bold uppercase tracking-widest mb-1.5">{side.label}</p>
                  <p className="text-[13px] text-[var(--text-primary)] leading-relaxed">{side.text}</p>
                  {side.quote && <p className="text-[11px] text-[var(--text-muted)] italic mt-2">&ldquo;{side.quote}&rdquo;</p>}
                </div>
              ))}
            </div>
            <div className="mt-4 flex items-start gap-2 bg-white rounded-lg p-3 border border-red-100">
              <span className="text-sm mt-px">💡</span>
              <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
                <strong className="text-[var(--text-primary)]">Why:</strong> {conflict.reason}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
