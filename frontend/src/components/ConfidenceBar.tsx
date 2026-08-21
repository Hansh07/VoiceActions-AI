"use client";

interface ConfidenceBarProps { confidence: number; verificationAgreement?: string; }

export default function ConfidenceBar({ confidence, verificationAgreement }: ConfidenceBarProps) {
  const color = confidence >= 80 ? "#16a34a" : confidence >= 50 ? "#d97706" : "#dc2626";
  const bg = confidence >= 80 ? "bg-green-50 border-green-200" : confidence >= 50 ? "bg-amber-50 border-amber-200" : "bg-red-50 border-red-200";
  const label = confidence >= 80 ? "High Confidence" : confidence >= 50 ? "Medium — Review Recommended" : "Low — Manual Review Required";
  const textClass = confidence >= 80 ? "text-green-700" : confidence >= 50 ? "text-amber-700" : "text-red-700";

  return (
    <div className={`rounded-xl p-4 border ${bg}`}>
      <div className="flex items-center justify-between mb-2.5">
        <span className="text-xs font-semibold text-[var(--text-secondary)]">📊 Overall Confidence</span>
        <span className={`text-2xl font-bold font-mono ${textClass}`}>{confidence}<span className="text-sm opacity-60">%</span></span>
      </div>
      <div className="w-full h-2.5 bg-white rounded-full overflow-hidden border border-[var(--border)]">
        <div className="h-full rounded-full confidence-fill" style={{ backgroundColor: color, width: `${confidence}%` }} />
      </div>
      <div className="flex items-center justify-between mt-2">
        <span className={`text-[11px] font-medium ${textClass}`}>{label}</span>
        {verificationAgreement && (
          <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${
            verificationAgreement === "full" ? "bg-green-100 text-green-700 border border-green-200"
            : verificationAgreement === "partial" ? "bg-amber-100 text-amber-700 border border-amber-200"
            : "bg-red-100 text-red-700 border border-red-200"
          }`}>🔍 Audit: {verificationAgreement}</span>
        )}
      </div>
    </div>
  );
}
