import React, { useState, useEffect } from 'react';
import { AlertCircle, X } from 'lucide-react';

import { Header } from './components/Header';
import { AgentGraph } from './components/AgentGraph';
import { ChatOrchestrator } from './components/ChatOrchestrator';
import { ArtifactViewer } from './components/ArtifactViewer';
import { VectorRAGViewer } from './components/VectorRAGViewer';
import { TraceabilityMatrix } from './components/TraceabilityMatrix';
import { VersionTimeline } from './components/VersionTimeline';
import { ConverterPanel } from './components/ConverterPanel';
import { EditorWorkspace } from './components/workspace/EditorWorkspace';
import { postJson, errorMessage } from './api';
import { AgentStep, EditResult, OrchestrationResult, SystemStatus } from './types';

const KEY_PROBLEMS: Record<string, string> = {
  missing: 'GEMINI_API_KEY is not set.',
  invalid: 'Google rejected GEMINI_API_KEY (invalid, expired, or not a Gemini API key).',
  unreachable: 'Gemini could not be reached (network problem or Google outage).',
};

export default function App() {
  const [activeTab, setActiveTab] = useState<string>('workspace');
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [downloadingZip, setDownloadingZip] = useState<boolean>(false);
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [lastResult, setLastResult] = useState<OrchestrationResult | null>(null);
  const [activeSteps, setActiveSteps] = useState<AgentStep[]>([]);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = async () => {
    try {
      const res = await fetch('/api/status');
      if (res.ok) setStatus(await res.json());
    } catch (err) {
      console.error('Failed to fetch status', err);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  const handleDownloadZip = () => {
    setDownloadingZip(true);
    const link = document.createElement('a');
    link.href = '/api/download-zip';
    link.setAttribute('download', 'multi_agent_doc_ppt_system.zip');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    setTimeout(() => setDownloadingZip(false), 1500);
  };

  const handleRunOrchestration = async (prompt: string, docTpl: string, pptTpl: string, focusDocs: string[]) => {
    setIsProcessing(true);
    setError(null);
    try {
      const data = await postJson<OrchestrationResult>('/api/orchestrate', {
        prompt,
        doc_template: docTpl,
        ppt_template: pptTpl,
        focus_docs: focusDocs,
      });
      setLastResult(data);
      setActiveSteps(data.execution_steps);
      await fetchStatus();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setIsProcessing(false);
    }
  };

  const handleRunEdit = async (instruction: string) => {
    setIsProcessing(true);
    setError(null);
    try {
      const data = await postJson<EditResult>('/api/conversational-edit', { instruction });
      const newStep: AgentStep = {
        step_num: activeSteps.length + 1,
        agent: 'Content Writer Agent',
        action: `Edit → ${data.version}`,
        detail: `"${instruction}": ${data.diff_summary.join('; ')}`,
        status: 'completed',
        artifacts: [data.artifacts.docx, data.artifacts.pptx],
      };
      setActiveSteps((prev) => [...prev, newStep]);
      // Keep the preview in sync with the edited files
      setLastResult((prev) => (prev ? { ...prev, content: data.content } : prev));
      await fetchStatus();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className={`${activeTab === 'workspace' ? 'min-h-screen lg:h-screen' : 'min-h-screen'} bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-blue-600 selection:text-white`}>
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onDownloadZip={handleDownloadZip}
        downloadingZip={downloadingZip}
        activeAgentsCount={9}
      />

      {activeTab === 'workspace' && <EditorWorkspace />}

      {activeTab !== 'workspace' && (
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {status && status.gemini_key_status !== 'ok' && (
          <div role="status" className="bg-amber-950/60 border border-amber-700 text-amber-200 text-sm rounded-xl p-4 space-y-1">
            <p className="font-semibold">{KEY_PROBLEMS[status.gemini_key_status ?? 'missing']}</p>
            <p>
              Generation, web research and image OCR need Gemini. Create a key at{' '}
              <a href="https://aistudio.google.com/apikey" target="_blank" rel="noreferrer" className="underline">aistudio.google.com/apikey</a>,
              set <code>GEMINI_API_KEY</code> in <code>.env</code> and restart <code>npm run dev</code>.
              The AI Editor Workspace keeps working with its built-in parser.
            </p>
          </div>
        )}

        {error && (
          <div role="alert" className="bg-red-950/60 border border-red-800 text-red-200 text-sm rounded-xl p-4 flex items-start gap-3">
            <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
            <span className="flex-1">{error}</span>
            <button onClick={() => setError(null)} aria-label="Dismiss error" className="cursor-pointer">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        <AgentGraph steps={activeSteps} isProcessing={isProcessing} />

        {activeTab === 'chat' && (
          <ChatOrchestrator
            onRunOrchestration={handleRunOrchestration}
            onRunEdit={handleRunEdit}
            onUploaded={fetchStatus}
            isProcessing={isProcessing}
            activeSteps={activeSteps}
            hasResult={lastResult !== null}
          />
        )}

        {activeTab === 'artifacts' && <ArtifactViewer result={lastResult} />}

        {activeTab === 'rag' && <VectorRAGViewer status={status} />}

        {activeTab === 'provenance' && (
          <TraceabilityMatrix citations={lastResult?.citations || []} content={lastResult?.content || null} />
        )}

        {activeTab === 'converter' && <ConverterPanel />}

        {activeTab === 'versions' && <VersionTimeline versions={status?.versions || []} />}
      </main>
      )}

      {activeTab !== 'workspace' && (
        <footer className="border-t border-slate-800/80 bg-slate-900/60 py-4 text-center text-xs text-slate-500">
          Multi-agent document and presentation generator • Gemini + Google Search + local RAG
        </footer>
      )}
    </div>
  );
}
