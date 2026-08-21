"use client";
import type { Ambiguity } from "@/lib/api";

interface AmbiguityFlagsProps { ambiguities: Ambiguity[]; }

export default function AmbiguityFlags({ ambiguities }: AmbiguityFlagsProps) {
  if (!ambiguities.length) return null;
  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-amber-700 flex items-center gap-2">
        <span className="w-6 h-6 rounded-lg bg-amber-50 border border-amber-200 flex items-center justify-center text-xs">❓</span>
        Needs Clarification
        <span className="ml-auto text-[11px] font-mono font-normal text-amber-600 bg-amber-50 border border-amber-100 px-2 py-0.5 rounded-full">{ambiguities.length} found</span>
      </h3>
      <div className="grid gap-2.5">
        {ambiguities.map((amb, i) => (
          <div key={i} className="rounded-xl p-4 bg-amber-50/50 border border-amber-200 animate-slide-up" style={{ animationDelay: `${i * 60}ms` }}>
            <div className="flex items-start gap-2.5 mb-2">
              <span className="text-base mt-0.5 shrink-0">🤷</span>
              <p className="text-[14px] text-[var(--text-primary)] italic leading-relaxed">&ldquo;{amb.quote}&rdquo;</p>
            </div>
            <div className="ml-8 space-y-1">
              <p className="text-xs text-[var(--text-secondary)]">
                <strong className="text-[var(--text-primary)]">What&apos;s unclear:</strong> {amb.what_is_unclear}
              </p>
              {amb.suggestion && <p className="text-xs text-amber-700"><strong>Needs:</strong> {amb.suggestion}</p>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
