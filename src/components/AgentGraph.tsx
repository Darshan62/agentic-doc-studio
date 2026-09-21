import React from 'react';
import { 
  Network, FileText, Presentation, Globe, Database, 
  CheckCircle, MessageSquare, RefreshCw, Cpu, ArrowRight 
} from 'lucide-react';
import { AgentStep } from '../types';

interface AgentGraphProps {
  steps: AgentStep[];
  isProcessing: boolean;
}

export const AgentGraph: React.FC<AgentGraphProps> = ({ steps, isProcessing }) => {
  const agents = [
    { id: 'supervisor', name: 'Supervisor Agent', icon: Network, role: 'Task Decomposition & Graph Routing', color: 'from-purple-600 to-indigo-600' },
    { id: 'doc_analyzer', name: 'Document Analyzer', icon: FileText, role: 'DOCX / PDF / OCR Layout & Style Extraction', color: 'from-blue-600 to-cyan-600' },
    { id: 'ppt_analyzer', name: 'PPT Analyzer', icon: Presentation, role: '16:9 Master Layouts & Theme Palette', color: 'from-amber-600 to-orange-600' },
    { id: 'web_researcher', name: 'Web Researcher', icon: Globe, role: 'Live Search & Multi-Angle Grounding', color: 'from-emerald-600 to-teal-600' },
    { id: 'rag_agent', name: 'Enterprise RAG Agent', icon: Database, role: 'Vector Search & Pinecone Cosine Retrieval', color: 'from-sky-600 to-blue-600' },
    { id: 'doc_gen', name: 'Doc Generator', icon: FileText, role: 'Pure OpenXML Word (.docx) Synthesis', color: 'from-blue-700 to-indigo-700' },
    { id: 'ppt_gen', name: 'PPT Generator', icon: Presentation, role: '12-Slide OpenXML Presentation (.pptx)', color: 'from-rose-600 to-red-600' },
    { id: 'validator', name: 'Validation Agent', icon: CheckCircle, role: 'Package Integrity & Slide Count QA', color: 'from-green-600 to-emerald-700' },
    { id: 'editor', name: 'Conversational Editor', icon: MessageSquare, role: 'In-Place Diffs & Version Auditing', color: 'from-violet-600 to-purple-700' },
  ];

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <Network className="w-5 h-5 text-indigo-400" />
          <h2 className="text-sm font-bold text-white uppercase tracking-wider">Multi-Agent System Architecture</h2>
        </div>
        <span className="text-xs bg-indigo-500/20 text-indigo-300 px-2.5 py-1 rounded-full border border-indigo-500/30 flex items-center space-x-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping"></span>
          <span>9 Autonomous Agents Active</span>
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {agents.map((ag) => {
          const Icon = ag.icon;
          const isRelated = steps.some((s) => s.agent.toLowerCase().includes(ag.name.toLowerCase().split(' ')[0]));
          return (
            <div
              key={ag.id}
              className={`p-3.5 rounded-lg border transition-all ${
                isRelated && isProcessing
                  ? 'border-blue-500/80 bg-blue-950/40 shadow-md shadow-blue-500/20'
                  : 'border-slate-800 bg-slate-800/50 hover:bg-slate-800'
              }`}
            >
              <div className="flex items-center space-x-3 mb-1.5">
                <div className={`w-8 h-8 rounded-lg bg-gradient-to-br ${ag.color} flex items-center justify-center text-white shadow`}>
                  <Icon className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-xs font-bold text-white leading-tight">{ag.name}</h3>
                  <span className="text-[10px] text-slate-400 font-mono">Specialized Agent</span>
                </div>
              </div>
              <p className="text-[11px] text-slate-300 line-clamp-2">{ag.role}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
};
