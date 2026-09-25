import React, { useState, useRef } from 'react';
import {
  Send, Sparkles, FileText, Presentation, Upload, RefreshCw, FileCheck, Clock, Pencil, BookOpen,
} from 'lucide-react';

import { postJson, errorMessage } from '../api';
import { AgentStep, UploadResult } from '../types';

const MAX_UPLOAD_MB = 25;
const DEFAULT_DOC_TEMPLATE = 'templates_and_samples/Company_Proposal.docx';
const DEFAULT_PPT_TEMPLATE = 'templates_and_samples/Company_Template.pptx';

interface UploadedFile {
  name: string;
  message: string;
  isError: boolean;
}

interface ChatOrchestratorProps {
  onRunOrchestration: (prompt: string, docTpl: string, pptTpl: string) => Promise<void>;
  onRunEdit: (instruction: string) => Promise<void>;
  onUploaded: () => void;
  isProcessing: boolean;
  activeSteps: AgentStep[];
  hasResult: boolean;
}

const EDIT_SUGGESTIONS = [
  'Add an executive summary slide.',
  'Make the presentation more concise.',
  'Add a competitive analysis section.',
];

function readAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = () => reject(new Error('Could not read the file'));
    reader.readAsDataURL(file);
  });
}

function describeUpload(result: UploadResult): string {
  if (!result.ingest) return 'Saved (used as a style template)';
  if (result.ingest.warning) return result.ingest.warning;
  return `Indexed ${result.ingest.words} words into ${result.ingest.chunks_indexed} chunks`;
}

export const ChatOrchestrator: React.FC<ChatOrchestratorProps> = ({
  onRunOrchestration,
  onRunEdit,
  onUploaded,
  isProcessing,
  activeSteps,
  hasResult,
}) => {
  const [prompt, setPrompt] = useState(
    'Research the latest Generative AI trends and create a proposal and slide deck using my uploaded files.'
  );
  const [docTemplate, setDocTemplate] = useState(DEFAULT_DOC_TEMPLATE);
  const [pptTemplate, setPptTemplate] = useState(DEFAULT_PPT_TEMPLATE);
  const [uploads, setUploads] = useState<UploadedFile[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const addUpload = (upload: UploadedFile) => setUploads((prev) => [upload, ...prev]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    // Reset so picking the same file again still fires onChange
    e.target.value = '';
    if (!file) return;

    if (file.size > MAX_UPLOAD_MB * 1024 * 1024) {
      addUpload({ name: file.name, message: `Too large (max ${MAX_UPLOAD_MB} MB)`, isError: true });
      return;
    }

    setIsUploading(true);
    try {
      const base64Content = await readAsDataUrl(file);
      const result = await postJson<UploadResult>('/api/upload', { filename: file.name, base64Content });
      if (result.filename.endsWith('.docx')) setDocTemplate(result.path);
      if (result.filename.endsWith('.pptx')) setPptTemplate(result.path);
      addUpload({ name: result.filename, message: describeUpload(result), isError: Boolean(result.ingest?.warning) });
      onUploaded();
    } catch (err) {
      addUpload({ name: file.name, message: errorMessage(err), isError: true });
    } finally {
      setIsUploading(false);
    }
  };

  const handleGenerate = (e: React.FormEvent) => {
    e.preventDefault();
    if (prompt.trim() && !isProcessing) onRunOrchestration(prompt, docTemplate, pptTemplate);
  };

  const handleEdit = () => {
    if (prompt.trim() && !isProcessing) onRunEdit(prompt);
  };

  return (
    <div className="space-y-6">
      {/* Templates and uploaded knowledge */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
          <div>
            <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center space-x-2">
              <FileCheck className="w-4 h-4 text-blue-400" />
              <span>Templates & Knowledge Files</span>
            </h2>
            <p className="text-xs text-slate-400">
              .docx / .pptx become style templates. PDF, DOCX, TXT and images are indexed so the agents can use them.
            </p>
          </div>

          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileUpload}
            className="hidden"
            accept=".docx,.pptx,.pdf,.txt,.md,.png,.jpg,.jpeg"
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading}
            className="flex items-center space-x-1.5 text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 px-3 py-1.5 rounded-lg transition-colors cursor-pointer disabled:opacity-50"
          >
            {isUploading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Upload className="w-3.5 h-3.5 text-blue-400" />}
            <span>{isUploading ? 'Uploading & indexing…' : 'Upload File'}</span>
          </button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="bg-slate-800/60 border border-slate-700/60 p-3 rounded-lg flex items-center space-x-3">
            <FileText className="w-8 h-8 text-blue-400 flex-shrink-0" />
            <div className="min-w-0">
              <span className="text-[10px] text-blue-300 font-bold uppercase block">Word Style Template</span>
              <p className="text-xs text-white font-medium truncate">{docTemplate.split('/').pop()}</p>
            </div>
          </div>
          <div className="bg-slate-800/60 border border-slate-700/60 p-3 rounded-lg flex items-center space-x-3">
            <Presentation className="w-8 h-8 text-amber-400 flex-shrink-0" />
            <div className="min-w-0">
              <span className="text-[10px] text-amber-300 font-bold uppercase block">Presentation Template</span>
              <p className="text-xs text-white font-medium truncate">{pptTemplate.split('/').pop()}</p>
            </div>
          </div>
        </div>

        {uploads.length > 0 && (
          <ul className="mt-3 space-y-1.5">
            {uploads.map((u, idx) => (
              <li key={`${u.name}-${idx}`} className="flex items-center gap-2 text-xs">
                <BookOpen className={`w-3.5 h-3.5 flex-shrink-0 ${u.isError ? 'text-red-400' : 'text-emerald-400'}`} />
                <span className="text-slate-200 truncate">{u.name}</span>
                <span className={u.isError ? 'text-red-300' : 'text-slate-400'}>— {u.message}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Prompt console */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
        <div>
          <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center space-x-2">
            <Sparkles className="w-4 h-4 text-cyan-400" />
            <span>Supervisor Command Console</span>
          </h2>
          <p className="text-xs text-slate-400">
            <b>Generate</b> creates a new proposal + deck. <b>Edit</b> changes the current one.
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          {EDIT_SUGGESTIONS.map((suggestion) => (
            <button
              key={suggestion}
              onClick={() => setPrompt(suggestion)}
              disabled={isProcessing || !hasResult}
              title={hasResult ? 'Use as an edit instruction' : 'Generate something first'}
              className="text-xs bg-slate-800/80 hover:bg-slate-700 text-slate-200 border border-slate-700 px-3 py-1.5 rounded-full transition-all cursor-pointer disabled:opacity-40"
            >
              {suggestion}
            </button>
          ))}
        </div>

        <form onSubmit={handleGenerate} className="space-y-3">
          <textarea
            rows={3}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Describe what to create, or how to change the current documents…"
            disabled={isProcessing}
            aria-label="Prompt"
            className="w-full bg-slate-950 border border-slate-700 rounded-xl p-3.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all resize-none"
          />
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={handleEdit}
              disabled={isProcessing || !prompt.trim() || !hasResult}
              className="bg-slate-800 hover:bg-slate-700 border border-slate-700 text-white text-xs font-semibold px-4 py-2.5 rounded-lg flex items-center space-x-2 disabled:opacity-40 cursor-pointer"
            >
              <Pencil className="w-3.5 h-3.5" />
              <span>Edit current</span>
            </button>
            <button
              type="submit"
              disabled={isProcessing || !prompt.trim()}
              className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white text-xs font-semibold px-4 py-2.5 rounded-lg flex items-center space-x-2 disabled:opacity-40 cursor-pointer"
            >
              {isProcessing ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
              <span>{isProcessing ? 'Agents working…' : 'Generate new'}</span>
            </button>
          </div>
        </form>
      </div>

      {/* Execution trace */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
        <div className="flex items-center space-x-2 mb-4">
          <Clock className="w-4 h-4 text-indigo-400" />
          <h3 className="text-sm font-bold text-white uppercase tracking-wider">Multi-Agent Execution Trace</h3>
        </div>

        {activeSteps.length === 0 ? (
          <p className="text-xs text-slate-400 text-center py-10 border border-dashed border-slate-800 rounded-lg">
            No runs yet. Upload files (optional), write a request and press <b>Generate new</b>.
          </p>
        ) : (
          <div className="space-y-3">
            {activeSteps.map((step) => (
              <div key={step.step_num} className="bg-slate-800/40 border border-slate-700/60 rounded-lg p-3 flex items-start space-x-3 text-xs">
                <div className="w-6 h-6 rounded-full bg-blue-500/20 text-blue-400 border border-blue-500/30 flex items-center justify-center font-mono font-bold flex-shrink-0 text-[11px] mt-0.5">
                  {step.step_num}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center space-x-2 mb-1">
                    <span className="font-bold text-slate-200">{step.agent}</span>
                    <span className="text-[10px] text-slate-400 font-mono">▸ {step.action}</span>
                  </div>
                  <p className="text-slate-300 leading-relaxed">{step.detail}</p>
                  {step.artifacts && step.artifacts.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {step.artifacts.map((art) => (
                        <span key={art} className="text-[10px] bg-slate-900 text-cyan-300 px-2 py-0.5 rounded border border-slate-700 font-mono">
                          {art}
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
