"use client";
import { useState } from "react";
import { searchActions } from "@/lib/api";

interface SearchResultItem { id: string; task: string; owner: string; similarity: number; }

export default function HistoryPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true); setSearched(true);
    try { const data = await searchActions(query); setResults(data.results || []); }
    catch { setResults([]); }
    finally { setLoading(false); }
  };

  return (
    <div className="max-w-3xl mx-auto px-6 py-10">
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-[var(--text-primary)] mb-1">Search Past Actions</h2>
        <p className="text-sm text-[var(--text-secondary)]">Semantic search over all your action items using Supabase pgvector.</p>
      </div>
      <div className="flex gap-2 mb-6">
        <input
          type="text" value={query} onChange={(e) => setQuery(e.target.value)} onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          placeholder="e.g. 'What tasks did I assign about marketing?'"
          className="flex-1 card-flat rounded-xl px-4 py-3 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-[var(--accent)] focus:ring-2 focus:ring-[var(--accent)]/10 transition-all"
        />
        <button onClick={handleSearch} disabled={loading || !query.trim()}
          className="px-5 py-3 bg-gradient-to-r from-indigo-500 to-purple-500 text-white rounded-xl text-sm font-semibold hover:opacity-90 transition-all disabled:opacity-40 shadow-md shadow-indigo-200">
          {loading ? "..." : "Search"}
        </button>
      </div>
      {searched && (
        <div className="space-y-3">
          {results.length === 0 ? (
            <div className="text-center py-12 text-[var(--text-muted)]">
              <p className="text-lg mb-1">🔍</p>
              <p className="text-sm">{loading ? "Searching..." : "No matching actions found."}</p>
            </div>
          ) : (
            <>
              <p className="text-xs text-[var(--text-muted)] mb-2">{results.length} results for &ldquo;{query}&rdquo;</p>
              {results.map((r, i) => (
                <div key={r.id} className="card-flat rounded-xl p-4 hover:border-[var(--accent)] transition-all animate-slide-up" style={{ animationDelay: `${i * 60}ms` }}>
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <p className="text-sm font-medium text-[var(--text-primary)]">{r.task}</p>
                      <p className="text-xs text-indigo-600 mt-1">👤 {r.owner}</p>
                    </div>
                    <span className="text-[10px] font-mono text-green-700 bg-green-50 border border-green-200 px-2 py-0.5 rounded-full">{(r.similarity * 100).toFixed(0)}% match</span>
                  </div>
                </div>
              ))}
            </>
          )}
        </div>
      )}
      {!searched && (
        <div className="mt-8 card-flat rounded-2xl p-6 text-center">
          <p className="text-sm text-[var(--text-secondary)] mb-1">Powered by <span className="text-indigo-600 font-semibold">Supabase pgvector</span></p>
          <p className="text-xs text-[var(--text-muted)]">Every action item is embedded as a vector. Search finds semantically similar results — even with different wording.</p>
        </div>
      )}
    </div>
  );
}
