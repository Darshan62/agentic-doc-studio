import React, { useState } from 'react';
import { Database, Search, FileText, RefreshCw } from 'lucide-react';

import { postJson, errorMessage } from '../api';
import { SystemStatus } from '../types';

interface SearchResult {
  title: string;
  doc: string;
  similarity: number;
  text: string;
}

interface VectorRAGViewerProps {
  status: SystemStatus | null;
}

export const VectorRAGViewer: React.FC<VectorRAGViewerProps> = ({ status }) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setIsSearching(true);
    setError(null);
    try {
      const data = await postJson<{ results: SearchResult[] }>('/api/search', { query });
      setResults(data.results);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
        <div className="flex items-center space-x-2">
          <Database className="w-5 h-5 text-sky-400" />
          <h2 className="text-sm font-bold text-white uppercase tracking-wider">
            Knowledge Base ({status?.kb_chunks_indexed ?? 0} chunks)
          </h2>
        </div>
        <p className="text-xs text-slate-400">
          Local SQLite store. Text is split into ~350-character chunks and embedded with a simple hashed word vector
          (no external embedding model), then ranked by cosine similarity.
        </p>
        <ul className="flex flex-wrap gap-2">
          {status?.kb_documents.map((doc) => (
            <li key={doc} className="text-[11px] bg-slate-800 border border-slate-700 text-slate-300 px-2 py-1 rounded flex items-center gap-1">
              <FileText className="w-3 h-3" /> {doc}
            </li>
          ))}
        </ul>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
        <form onSubmit={handleSearch} className="flex gap-2">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search your knowledge base…"
            aria-label="Search query"
            className="flex-1 bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-blue-500"
          />
          <button type="submit" disabled={isSearching || !query.trim()}
            className="bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold px-4 rounded-lg flex items-center gap-2 disabled:opacity-40 cursor-pointer">
            {isSearching ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />} Search
          </button>
        </form>

        {error && <p role="alert" className="text-xs text-red-300">{error}</p>}

        <div className="space-y-3">
          {results.map((r, idx) => (
            <div key={idx} className="bg-slate-800/40 border border-slate-700/60 rounded-lg p-3 text-xs space-y-1">
              <div className="flex justify-between gap-2">
                <span className="font-bold text-slate-200 truncate">{r.doc}</span>
                <span className="text-sky-300 font-mono">{Math.round(r.similarity * 100)}% match</span>
              </div>
              <p className="text-slate-300">{r.text}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
