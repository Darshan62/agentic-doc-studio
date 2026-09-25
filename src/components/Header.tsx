import React from 'react';
import { Download, Bot, Sparkles, FileArchive, CheckCircle2, ShieldCheck } from 'lucide-react';

interface HeaderProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  onDownloadZip: () => void;
  downloadingZip: boolean;
  activeAgentsCount: number;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  setActiveTab,
  onDownloadZip,
  downloadingZip,
  activeAgentsCount,
}) => {
  const navTabs = [
    { id: 'workspace', label: 'AI Editor Workspace' },
    { id: 'chat', label: 'Chat & Orchestrator' },
    { id: 'artifacts', label: 'Generated DOCX & 12-Slide Deck' },
    { id: 'rag', label: 'Enterprise RAG & Vectors' },
    { id: 'provenance', label: 'Traceability & Citations' },
    { id: 'converter', label: 'Bidirectional Converter' },
    { id: 'versions', label: 'Version Audit Trail' },
  ];

  return (
    <header className="bg-slate-900 border-b border-slate-800 text-white sticky top-0 z-50">
      {/* Top Banner */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-600 to-indigo-800 flex items-center justify-center shadow-lg shadow-blue-500/20">
            <Bot className="w-6 h-6 text-white" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-lg font-bold tracking-tight text-white">DocuSynth Enterprise</h1>
              <span className="px-2 py-0.5 text-xs font-semibold bg-blue-500/20 text-blue-300 rounded border border-blue-500/30">
                Multi-Agent POC
              </span>
              <span className="px-2 py-0.5 text-xs font-medium bg-emerald-500/20 text-emerald-300 rounded border border-emerald-500/30 flex items-center space-x-1">
                <CheckCircle2 className="w-3 h-3 mr-1" /> ECMA-376 OpenXML
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Autonomous Document & 16:9 Presentation Synthesis with Real-Time Web & Vector RAG
            </p>
          </div>
        </div>

        {/* Right action items */}
        <div className="flex items-center space-x-3">
          <div className="hidden md:flex items-center space-x-2 text-xs text-slate-400 bg-slate-800/80 px-3 py-1.5 rounded-lg border border-slate-700">
            <ShieldCheck className="w-4 h-4 text-indigo-400" />
            <span>9 Agents Orchestrated</span>
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
          </div>

          {/* Download Project ZIP Button */}
          <button
            onClick={onDownloadZip}
            disabled={downloadingZip}
            className="flex items-center space-x-2 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white text-xs font-semibold px-4 py-2 rounded-lg transition-all shadow-md hover:shadow-cyan-500/20 disabled:opacity-50 cursor-pointer"
            title="Download full project repository as ZIP archive"
          >
            <FileArchive className="w-4 h-4" />
            <span>{downloadingZip ? 'Packaging ZIP...' : 'Download Project ZIP'}</span>
            <span className="text-[10px] bg-black/30 px-1.5 py-0.5 rounded">0.13 MB</span>
          </button>
        </div>
      </div>

      {/* Navigation tabs */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 border-t border-slate-800/60 overflow-x-auto">
        <nav className="flex space-x-1 py-1">
          {navTabs.map((tab) => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-3 py-2 text-xs font-medium rounded-md whitespace-nowrap transition-colors cursor-pointer ${
                  isActive
                    ? 'bg-blue-600 text-white font-semibold'
                    : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                }`}
              >
                {tab.label}
              </button>
            );
          })}
        </nav>
      </div>
    </header>
  );
};
