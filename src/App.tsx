import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { AgentGraph } from './components/AgentGraph';
import { ChatOrchestrator } from './components/ChatOrchestrator';
import { ArtifactViewer } from './components/ArtifactViewer';
import { VectorRAGViewer } from './components/VectorRAGViewer';
import { TraceabilityMatrix } from './components/TraceabilityMatrix';
import { VersionTimeline } from './components/VersionTimeline';
import { ConverterPanel } from './components/ConverterPanel';
import { AgentStep, OrchestrationResult, SystemStatus } from './types';

export default function App() {
  const [activeTab, setActiveTab] = useState<string>('chat');
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [downloadingZip, setDownloadingZip] = useState<boolean>(false);
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [lastResult, setLastResult] = useState<OrchestrationResult | null>(null);
  const [activeSteps, setActiveSteps] = useState<AgentStep[]>([
    {
      step_num: 1,
      agent: 'Supervisor Agent',
      action: 'Task Decomposition',
      detail: "Decomposing prompt: 'Research the latest Generative AI trends and create a proposal and 12-slide presentation' into 7-stage execution graph.",
      status: 'completed',
    },
    {
      step_num: 2,
      agent: 'Document Analyzer',
      action: 'Analyze Document Template',
      detail: 'Extracted typography (Georgia & Arial), brand palette (#1B365D & #00A3E0), and formal executive tone from Company_Proposal.docx.',
      status: 'completed',
    },
    {
      step_num: 3,
      agent: 'PPT Analyzer',
      action: 'Analyze PPT Template',
      detail: 'Extracted 16:9 widescreen master geometry and theme palette (#0F2D59 Navy, #2563EB Royal Blue, #10B981 Emerald) from Company_Template.pptx.',
      status: 'completed',
    },
    {
      step_num: 4,
      agent: 'Web Researcher',
      action: 'Execute Web Research',
      detail: 'Queried 2025 AI benchmarks from Gartner, McKinsey, Stanford AI Index, MIT Review, and IDC. Registered verified citations [Web-1] to [Web-5].',
      status: 'completed',
    },
    {
      step_num: 5,
      agent: 'Enterprise RAG Agent',
      action: 'Retrieve Enterprise Knowledge',
      detail: 'Queried vector store with semantic embeddings; retrieved internal corporate strategy and zero-trust security standards [RAG-1].',
      status: 'completed',
    },
    {
      step_num: 6,
      agent: 'Doc Generator',
      action: 'Generate Editable DOCX',
      detail: 'Synthesized pure OpenXML Word proposal with Title, Executive Summary callout, tables, and citation footnotes.',
      status: 'completed',
      artifacts: ['output/Company_Proposal_Generated.docx'],
    },
    {
      step_num: 7,
      agent: 'PPT Generator',
      action: 'Generate Editable 12-Slide PPTX',
      detail: 'Synthesized 16:9 widescreen presentation matching template palette, 3-pillar cards, and metrics.',
      status: 'completed',
      artifacts: ['output/Company_Presentation_Generated.pptx'],
    },
    {
      step_num: 8,
      agent: 'Validation Agent',
      action: 'Validate OpenXML & Slide Count',
      detail: 'DOCX Validation: PASSED (Score 100%). PPTX Validation: PASSED (Exact 12 Slides, Score 100%). 0 ungrounded claims.',
      status: 'completed',
    },
  ]);

  // Fetch initial system status
  const fetchStatus = async () => {
    try {
      const res = await fetch('/api/status');
      if (res.ok) {
        const data = await res.json();
        setStatus(data);
      }
    } catch (err) {
      console.error('Failed to fetch status', err);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  // Download project ZIP directly
  const handleDownloadZip = () => {
    setDownloadingZip(true);
    const link = document.createElement('a');
    link.href = '/api/download-zip';
    link.setAttribute('download', 'multi_agent_doc_ppt_system.zip');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    setTimeout(() => {
      setDownloadingZip(false);
    }, 1500);
  };

  // Run full orchestration
  const handleRunOrchestration = async (prompt: string, docTpl: string, pptTpl: string) => {
    setIsProcessing(true);
    try {
      const res = await fetch('/api/orchestrate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, doc_template: docTpl, ppt_template: pptTpl }),
      });
      const data = await res.json();
      if (data.status === 'success') {
        setLastResult(data);
        if (data.execution_steps && data.execution_steps.length > 0) {
          setActiveSteps(data.execution_steps);
        }
        await fetchStatus();
      }
    } catch (err) {
      console.error('Orchestration failed', err);
    } finally {
      setIsProcessing(false);
    }
  };

  // Run conversational edit
  const handleRunEdit = async (instruction: string) => {
    setIsProcessing(true);
    try {
      const res = await fetch('/api/conversational-edit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ instruction }),
      });
      const data = await res.json();
      if (data.status === 'success') {
        const newStep: AgentStep = {
          step_num: activeSteps.length + 1,
          agent: 'Conversational Editing Agent',
          action: `Edit: ${data.action_type}`,
          detail: `Instruction: '${instruction}'. Diffs: ${data.diff_summary?.join('; ')}`,
          status: 'completed',
          artifacts: [data.artifacts?.docx, data.artifacts?.pptx],
        };
        setActiveSteps((prev) => [...prev, newStep]);
        await fetchStatus();
      }
    } catch (err) {
      console.error('Edit failed', err);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-blue-600 selection:text-white">
      {/* Header with Project ZIP Download */}
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onDownloadZip={handleDownloadZip}
        downloadingZip={downloadingZip}
        activeAgentsCount={9}
      />

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* Visual Architecture Graph */}
        <AgentGraph steps={activeSteps} isProcessing={isProcessing} />

        {/* Tab Views */}
        {activeTab === 'chat' && (
          <ChatOrchestrator
            onRunOrchestration={handleRunOrchestration}
            onRunEdit={handleRunEdit}
            isProcessing={isProcessing}
            activeSteps={activeSteps}
            lastResult={lastResult}
            status={status}
          />
        )}

        {activeTab === 'artifacts' && <ArtifactViewer result={lastResult} />}

        {activeTab === 'rag' && <VectorRAGViewer status={status} />}

        {activeTab === 'provenance' && (
          <TraceabilityMatrix citations={lastResult?.citations || []} />
        )}

        {activeTab === 'converter' && <ConverterPanel />}

        {activeTab === 'versions' && (
          <VersionTimeline versions={status?.versions || []} />
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/80 bg-slate-900/60 py-4 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 flex flex-wrap items-center justify-between gap-2">
          <span>DocuSynth Enterprise Multi-Agent POC • ECMA-376 OpenXML Standards Compliant</span>
          <span>Zero-Desktop Dependencies • 16:9 Widescreen W3C Standards</span>
        </div>
      </footer>
    </div>
  );
}
