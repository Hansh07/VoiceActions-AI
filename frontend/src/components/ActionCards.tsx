"use client";
import type { ActionItem } from "@/lib/api";

interface ActionCardsProps { actions: ActionItem[]; }

export default function ActionCards({ actions }: ActionCardsProps) {
  if (!actions.length) return null;
  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-[var(--text-primary)] flex items-center gap-2">
        <span className="w-6 h-6 rounded-lg bg-green-50 border border-green-200 flex items-center justify-center text-xs">✅</span>
        Action Items
        <span className="ml-auto text-[11px] font-mono font-normal text-[var(--text-muted)] bg-[var(--bg-secondary)] border border-[var(--border)] px-2 py-0.5 rounded-full">{actions.length} found</span>
      </h3>
      <div className="grid gap-2.5">
        {actions.map((action, i) => (
          <div key={i} className="card-flat rounded-xl p-4 animate-slide-up" style={{ animationDelay: `${i * 60}ms` }}>
            <p className="text-[14px] font-medium text-[var(--text-primary)] leading-relaxed mb-3">{action.task}</p>
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-1 text-[11px] text-indigo-600 bg-indigo-50 border border-indigo-100 px-2 py-0.5 rounded-full font-medium">
                <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="8" r="4"/><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/></svg>
                {action.owner}
              </span>
              {action.deadline && action.deadline !== "not specified" && (
                <span className="text-[11px] text-[var(--text-muted)] bg-[var(--bg-secondary)] border border-[var(--border)] px-2 py-0.5 rounded-full">📅 {action.deadline}</span>
              )}
              <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold uppercase tracking-wider badge-${action.priority}`}>{action.priority}</span>
            </div>
            {action.source_quote && (
              <div className="mt-3 pl-3 border-l-2 border-[var(--border)]">
                <p className="text-[11px] text-[var(--text-muted)] italic leading-relaxed">&ldquo;{action.source_quote}&rdquo;</p>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
