import React, { useState, useRef } from 'react';
import { 
  Send, Sparkles, FileText, Presentation, Image, Upload, 
  CheckCircle2, AlertCircle, Clock, ArrowRight, RefreshCw, FileCheck 
} from 'lucide-react';
import { AgentStep, OrchestrationResult, SystemStatus } from '../types';

interface ChatOrchestratorProps {
  onRunOrchestration: (prompt: string, docTpl: string, pptTpl: string) => Promise<void>;
  onRunEdit: (instruction: string) => Promise<void>;
  isProcessing: boolean;
  activeSteps: AgentStep[];
  lastResult: OrchestrationResult | null;
  status: SystemStatus | null;
}

export const ChatOrchestrator: React.FC<ChatOrchestratorProps> = ({
  onRunOrchestration,
  onRunEdit,
  isProcessing,
  activeSteps,
  lastResult,
  status,
}) => {
  const [prompt, setPrompt] = useState(
    'Research the latest Generative AI trends and create a proposal and 12-slide presentation using the same tone and style as the uploaded files.'
  );
  const [selectedDoc, setSelectedDoc] = useState('templates_and_samples/Company_Proposal.docx');
  const [selectedPpt, setSelectedPpt] = useState('templates_and_samples/Company_Template.pptx');
  const [uploadedFiles, setUploadedFiles] = useState<string[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const quickPrompts = [
    { label: '🚀 Primary Assignment Generation', prompt: 'Research the latest Generative AI trends and create a proposal and 12-slide presentation using the same tone and style as the uploaded files.', isNewRun: true },
    { label: '📝 "Add an executive summary."', prompt: 'Add an executive summary.', isNewRun: false },
    { label: '⚡ "Make the presentation more concise."', prompt: 'Make the presentation more concise.', isNewRun: false },
    { label: '📊 "Add a competitive analysis section."', prompt: 'Add a competitive analysis section.', isNewRun: false },
    { label: '🌐 "Update the report using the latest web information."', prompt: 'Update the report using the latest web information.', isNewRun: false },
  ];

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = async () => {
      try {
        const base64 = reader.result as string;
        const res = await fetch('/api/upload', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ filename: file.name, base64Content: base64 }),
        });
        const data = await res.json();
        if (data.status === 'uploaded') {
          setUploadedFiles((prev) => [...prev, data.path]);
          if (file.name.endsWith('.docx')) setSelectedDoc(data.path);
          if (file.name.endsWith('.pptx')) setSelectedPpt(data.path);
        }
      } catch (err) {
        console.error('Upload failed', err);
      }
    };
    reader.readAsDataURL(file);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim() || isProcessing) return;

    // If it's a conversational edit phrase or result already exists
    const isEdit = !prompt.toLowerCase().includes('research') && (lastResult !== null || prompt.toLowerCase().includes('add') || prompt.toLowerCase().includes('make') || prompt.toLowerCase().includes('update'));
    if (isEdit && lastResult) {
      onRunEdit(prompt);
    } else {
      onRunOrchestration(prompt, selectedDoc, selectedPpt);
    }
  };

  return (
    <div className="space-y-6">
      {/* Template & Ingestion Context Bar */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
          <div>
            <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center space-x-2">
              <FileCheck className="w-4 h-4 text-blue-400" />
              <span>Uploaded Template Context & Ingestion Pipeline</span>
            </h2>
            <p className="text-xs text-slate-400">
              Analyzed for typography (Georgia/Arial), brand color palettes, margins, and 16:9 layouts
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileUpload}
              className="hidden"
              accept=".docx,.pptx,.pdf,.png,.jpg"
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              className="flex items-center space-x-1.5 text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 px-3 py-1.5 rounded-lg transition-colors cursor-pointer"
            >
              <Upload className="w-3.5 h-3.5 text-blue-400" />
              <span>Upload Custom Template</span>
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="bg-slate-800/60 border border-slate-700/60 p-3 rounded-lg flex items-center space-x-3">
            <FileText className="w-8 h-8 text-blue-400 flex-shrink-0" />
            <div className="min-w-0">
              <span className="text-[10px] text-blue-300 font-bold uppercase block">Word Style Template</span>
              <p className="text-xs text-white font-medium truncate">{selectedDoc.split('/').pop()}</p>
              <span className="text-[10px] text-slate-400">Georgia & Arial • #1B365D Navy</span>
            </div>
          </div>

          <div className="bg-slate-800/60 border border-slate-700/60 p-3 rounded-lg flex items-center space-x-3">
            <Presentation className="w-8 h-8 text-amber-400 flex-shrink-0" />
            <div className="min-w-0">
              <span className="text-[10px] text-amber-300 font-bold uppercase block">Presentation Template</span>
              <p className="text-xs text-white font-medium truncate">{selectedPpt.split('/').pop()}</p>
              <span className="text-[10px] text-slate-400">16:9 Widescreen • #0F2D59 & #2563EB</span>
            </div>
          </div>

          <div className="bg-slate-800/60 border border-slate-700/60 p-3 rounded-lg flex items-center space-x-3">
            <Image className="w-8 h-8 text-emerald-400 flex-shrink-0" />
            <div className="min-w-0">
              <span className="text-[10px] text-emerald-300 font-bold uppercase block">Vision OCR Brief</span>
              <p className="text-xs text-white font-medium truncate">Scanned_Architecture_Brief.png</p>
              <span className="text-[10px] text-slate-400">Multi-Modal Zone OCR • 94% Conf</span>
            </div>
          </div>
        </div>
      </div>

      {/* Interactive Chat & Prompt Execution Console */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
        <div>
          <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center space-x-2">
            <Sparkles className="w-4 h-4 text-cyan-400" />
            <span>Supervisor Command Console</span>
          </h2>
          <p className="text-xs text-slate-400">
            Send high-level research requests or natural-language conversational revision instructions
          </p>
        </div>

        {/* Quick prompt badges */}
        <div className="flex flex-wrap gap-2">
          {quickPrompts.map((qp, idx) => (
            <button
              key={idx}
              onClick={() => {
                setPrompt(qp.prompt);
                if (qp.isNewRun) {
                  onRunOrchestration(qp.prompt, selectedDoc, selectedPpt);
                } else {
                  onRunEdit(qp.prompt);
                }
              }}
              disabled={isProcessing}
              className="text-xs bg-slate-800/80 hover:bg-slate-700 text-slate-200 border border-slate-700 px-3 py-1.5 rounded-full transition-all hover:border-blue-500/50 cursor-pointer disabled:opacity-50 text-left"
            >
              {qp.label}
            </button>
          ))}
        </div>

        {/* Form Input */}
        <form onSubmit={handleSubmit} className="relative">
          <textarea
            rows={3}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Type instructions for document and presentation synthesis or revisions..."
            disabled={isProcessing}
            className="w-full bg-slate-950 border border-slate-700 rounded-xl p-3.5 pr-28 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all resize-none"
          />
          <button
            type="submit"
            disabled={isProcessing || !prompt.trim()}
            className="absolute bottom-3 right-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white text-xs font-semibold px-4 py-2.5 rounded-lg flex items-center space-x-2 transition-all shadow-md hover:shadow-indigo-500/20 disabled:opacity-40 cursor-pointer"
          >
            {isProcessing ? (
              <>
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                <span>Executing...</span>
              </>
            ) : (
              <>
                <span>Run Agent</span>
                <Send className="w-3.5 h-3.5" />
              </>
            )}
          </button>
        </form>
      </div>

      {/* Real-time Agent Execution Trace */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            <Clock className="w-4 h-4 text-indigo-400" />
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">Multi-Agent Execution Trace</h3>
          </div>
          {isProcessing && (
            <span className="text-xs text-blue-400 flex items-center space-x-1.5 animate-pulse">
              <span className="w-2 h-2 rounded-full bg-blue-500"></span>
              <span>Supervisor Dispatching Steps...</span>
            </span>
          )}
        </div>

        {activeSteps.length === 0 ? (
          <div className="text-center py-10 border border-dashed border-slate-800 rounded-lg">
            <p className="text-xs text-slate-400">
              No active execution trace. Click one of the prompt triggers above to launch the 7-stage workflow!
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {activeSteps.map((step, idx) => (
              <div
                key={idx}
                className="bg-slate-800/40 border border-slate-700/60 rounded-lg p-3 flex items-start space-x-3 text-xs transition-all hover:bg-slate-800/70"
              >
                <div className="w-6 h-6 rounded-full bg-blue-500/20 text-blue-400 border border-blue-500/30 flex items-center justify-center font-mono font-bold flex-shrink-0 text-[11px] mt-0.5">
                  {step.step_num}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <div className="flex items-center space-x-2">
                      <span className="font-bold text-slate-200">{step.agent}</span>
                      <span className="text-[10px] text-slate-400 font-mono">▸ {step.action}</span>
                    </div>
                    <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                      COMPLETED
                    </span>
                  </div>
                  <p className="text-slate-300 text-xs leading-relaxed">{step.detail}</p>
                  {step.artifacts && step.artifacts.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {step.artifacts.map((art, aIdx) => (
                        <span key={aIdx} className="text-[10px] bg-slate-900 text-cyan-300 px-2 py-0.5 rounded border border-slate-700 font-mono">
                          📁 {art}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
