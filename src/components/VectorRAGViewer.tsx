import React, { useState } from 'react';
import { Database, Search, FileText, CheckCircle2, ShieldAlert, Cpu } from 'lucide-react';
import { SystemStatus } from '../types';

interface VectorRAGViewerProps {
  status: SystemStatus | null;
}

export const VectorRAGViewer: React.FC<VectorRAGViewerProps> = ({ status }) => {
  const [query, setQuery] = useState('multi-agent architecture and autonomous task execution');
  const [searchResults, setSearchResults] = useState<any[]>([
    {
      title: 'Acme Enterprise AI Strategy & Governance Directive (Part 1)',
      doc: 'Acme_Enterprise_AI_Strategy_2025.txt',
      similarity: 0.94,
      text: 'Acme Global Solutions mandates the deployment of specialized multi-agent architectures across all document generation and executive presentation workflows. Monolithic single-prompt large language models are prohibited due to unconstrained hallucination risks.',
    },
    {
      title: 'Acme Enterprise AI Strategy (Part 2: Vector Database)',
      doc: 'Acme_Enterprise_AI_Strategy_2025.txt',
      similarity: 0.88,
      text: 'All generative tasks must be anchored in the Enterprise Knowledge Base via dense vector embeddings. The vector database must support cosine similarity retrieval with a minimum similarity threshold of 0.70. Sliding-window chunking (350 char window, 60 overlap).',
    },
    {
      title: 'Acme Information Security Standards',
      doc: 'Acme_Security_and_Governance_Standards.txt',
      similarity: 0.81,
      text: 'Customer prompt data, uploaded document templates, and enterprise documents shall remain strictly within dedicated tenant VPC boundaries. No data uploaded or generated shall be used to fine-tune or train external foundational models.',
    },
  ]);

  return (
    <div className="space-y-6">
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            <Database className="w-5 h-5 text-sky-400" />
            <h2 className="text-sm font-bold text-white uppercase tracking-wider">
              Enterprise Vector Database & RAG Retrieval
            </h2>
          </div>
          <span className="text-xs bg-sky-500/20 text-sky-300 px-2.5 py-1 rounded-full border border-sky-500/30">
            {status?.kb_chunks_indexed || 16} Chunks Indexed • Pinecone / SQLite Architecture
          </span>
        </div>
        <p className="text-xs text-slate-400">
          Dense vector embeddings with character n-grams and cosine similarity search for enterprise data grounding
        </p>

        {/* Indexed documents cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-4">
          <div className="bg-slate-800/50 border border-slate-700 p-3 rounded-lg">
            <div className="flex items-center space-x-2 mb-1">
              <FileText className="w-4 h-4 text-sky-400" />
              <span className="text-xs font-bold text-white">Acme AI Strategy 2025</span>
            </div>
            <p className="text-[11px] text-slate-400">8 Chunks • Multi-agent directives, SLAs, & format policies</p>
          </div>
          <div className="bg-slate-800/50 border border-slate-700 p-3 rounded-lg">
            <div className="flex items-center space-x-2 mb-1">
              <FileText className="w-4 h-4 text-emerald-400" />
              <span className="text-xs font-bold text-white">Security & Zero-Trust</span>
            </div>
            <p className="text-[11px] text-slate-400">4 Chunks • VPC isolation, RBAC, & provenance rules</p>
          </div>
          <div className="bg-slate-800/50 border border-slate-700 p-3 rounded-lg">
            <div className="flex items-center space-x-2 mb-1">
              <FileText className="w-4 h-4 text-amber-400" />
              <span className="text-xs font-bold text-white">Market Expansion Brief</span>
            </div>
            <p className="text-[11px] text-slate-400">4 Chunks • TAM targets & competitive differentiation</p>
          </div>
        </div>
      </div>

      {/* Semantic Search Sandbox */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
        <div>
          <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center space-x-2">
            <Search className="w-4 h-4 text-blue-400" />
            <span>Semantic Vector Search Sandbox</span>
          </h3>
          <p className="text-xs text-slate-400">Test cosine similarity retrieval against indexed corporate knowledge</p>
        </div>

        <div className="flex space-x-2">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="flex-1 bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
            placeholder="Search query..."
          />
          <button
            onClick={() => {}}
            className="bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold px-4 py-2 rounded-lg transition-colors cursor-pointer"
          >
            Vector Search
          </button>
        </div>

        {/* Results */}
        <div className="space-y-3">
          {searchResults.map((r, idx) => (
            <div key={idx} className="bg-slate-800/40 border border-slate-700/60 p-3.5 rounded-lg text-xs space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="font-bold text-white">{r.title}</span>
                <span className="text-[10px] bg-emerald-500/20 text-emerald-300 px-2 py-0.5 rounded border border-emerald-500/30">
                  Cosine Match: {Math.round(r.similarity * 100)}%
                </span>
              </div>
              <p className="text-slate-300 leading-relaxed">{r.text}</p>
              <div className="text-[10px] text-slate-500 font-mono">Source File: {r.doc}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
