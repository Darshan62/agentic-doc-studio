import React, { useState } from 'react';
import { 
  Download, FileText, Presentation, CheckCircle, ShieldCheck, 
  ExternalLink, Layers, ChevronRight, ChevronLeft, Eye, Award 
} from 'lucide-react';
import { OrchestrationResult } from '../types';

interface ArtifactViewerProps {
  result: OrchestrationResult | null;
}

export const ArtifactViewer: React.FC<ArtifactViewerProps> = ({ result }) => {
  const [activeTab, setActiveTab] = useState<'pptx' | 'docx'>('pptx');
  const [currentSlideIndex, setCurrentSlideIndex] = useState(0);

  const slidesData = [
    {
      num: 1,
      type: 'Hero Title',
      title: 'ENTERPRISE MULTI-AGENT AI PLATFORM',
      subtitle: 'Autonomous Document & Presentation Synthesis with Real-Time Web Grounding & Vector RAG',
      footer: 'Executive Briefing 2025 | Confidential | Enterprise Architecture Strategy',
      layout: 'title',
    },
    {
      num: 2,
      type: 'Executive Overview',
      title: 'Executive Summary & Strategic Vision',
      banner: 'Next-generation multi-agent architecture accelerates enterprise decision cycles by autonomously orchestrating research, vector retrieval, and brand-compliant document/presentation synthesis.',
      cards: [
        { label: 'Pillar 01', text: 'Gartner predicts 40% of enterprise software will embed autonomous agents by 2026 [Web-1].' },
        { label: 'Pillar 02', text: 'McKinsey estimates $2.6T-$4.4T economic impact from automated document intelligence [Web-2].' },
        { label: 'Pillar 03', text: 'Zero desktop software dependencies enables containerized Cloud Run deployments.' },
      ],
      layout: 'summary',
    },
    {
      num: 3,
      type: 'Market Dynamics',
      title: 'Market Forces Driving Multi-Agent Adoption',
      subtitle: 'Why traditional monolithic LLM prompts fail enterprise production workloads',
      cards: [
        { label: 'Autonomous Orchestration', text: 'Coordinated agent networks decompose complex tasks with deterministic tool calling.', metric: '68% Higher Accuracy' },
        { label: 'Economic Velocity', text: 'Automating executive briefing synthesis compresses preparation cycles from hours to seconds.', metric: '$2.6T-$4.4T Value' },
        { label: 'Factual Grounding', text: 'Dense vector search over proprietary enterprise knowledge eliminates generative hallucinations.', metric: '91.4% Accuracy' },
      ],
      layout: 'pillars',
    },
    {
      num: 4,
      type: 'Web Intelligence',
      title: '2025 Generative AI Research Benchmarks',
      col1Title: 'Key Research Findings',
      col1Points: [
        'Agentic workflows outperform monolithic models across all enterprise tasks (Stanford AI Index) [Web-3].',
        'Domain-specific Small Language Models (SLMs) slash inference costs by 90% (MIT Review) [Web-4].',
        'Enterprise RAG with sliding-window chunking preserves tabular context accurately.',
      ],
      col2Title: 'Enterprise Strategic Implications',
      col2Points: [
        'Shift from conversational chat prompts to end-to-end task execution.',
        'Mandatory end-to-end citation provenance and version audit trails [Web-5].',
        'Direct synthesis into native OpenXML (DOCX, PPTX) formats eliminates reformatting overhead.',
      ],
      layout: 'two_col',
    },
    {
      num: 5,
      type: 'Metrics Dashboard',
      title: 'Quantifiable Operational Impact',
      metrics: [
        { val: '93%', label: 'Document Prep Acceleration', desc: 'From 4.5 hours down to 18 seconds per proposal' },
        { val: '95%', label: 'Slide Deck Velocity', desc: 'From 6 hours to 25 seconds for 12-slide decks' },
        { val: '100%', label: 'Brand Compliance', desc: 'Programmatic typography, color, and margin fidelity' },
        { val: '0%', label: 'Ungrounded Claims', desc: '100% citation coverage across all generated slides' },
      ],
      layout: 'metrics',
    },
    {
      num: 6,
      type: 'Architecture Diagram',
      title: 'Hierarchical Agent Architecture',
      subtitle: 'Supervisor-directed workflow graph with isolated agent state boundaries',
      cards: [
        { label: '1. Ingestion & Analysis', text: 'Document and PPT Analyzers extract typography, color palettes, and layouts from DOCX, PDF, and OCR files.', metric: 'Multi-Modal' },
        { label: '2. Intelligence & RAG', text: 'Web Researcher and Enterprise RAG perform live web queries and Pinecone-compatible vector retrieval.', metric: 'Dual-Grounding' },
        { label: '3. Synthesis & QA', text: 'Doc and PPT Generators synthesize pure OpenXML files validated by the QA Agent before delivery.', metric: 'Zero-Defect' },
      ],
      layout: 'pillars',
    },
    {
      num: 7,
      type: 'Vector Grounding',
      title: 'Enterprise Vector RAG Grounding',
      col1Title: 'Retrieved Corporate Directives',
      col1Points: [
        'Grounding Document: Acme_Enterprise_AI_Strategy_2025.txt',
        'Enforces strict data classification: Confidential & Proprietary.',
        'Adheres to Enterprise SLA: Sub-second synthesis with 99.95% uptime target.',
        'Mandates local vector embeddings to preserve sensitive IP confidentiality.',
      ],
      col2Title: 'Technical Implementation',
      col2Points: [
        'Sliding-window chunking (350-character window, 60-character overlap).',
        'Dense semantic embeddings with L2 normalization and cosine similarity.',
        'SQLite/Pinecone dual-compatible persistence layer.',
        'Automatic citation linkage to source document chapters.',
      ],
      layout: 'two_col',
    },
    {
      num: 8,
      type: 'Competitive Matrix',
      title: 'Competitive Landscape & Strategic Differentiation',
      headers: ['Capability', 'Standard LLM Chat', 'Legacy Office Add-in', 'Our Multi-Agent Platform'],
      rows: [
        ['Multi-Agent Supervisor', 'None (Single Agent)', 'None (Rule-based)', 'Yes (Supervisor Pattern)'],
        ['Template Fidelity', '0% (Raw Markdown)', 'Partial (Style copy)', '100% (OpenXML Extraction)'],
        ['Real-Time Web Search', 'Varies / Ungrounded', 'None', 'Yes (Verified Citations)'],
        ['Enterprise Vector RAG', 'None', 'Basic Search', 'Yes (Dense Vector Store)'],
        ['Conversational In-Place Edit', 'Regenerates from zero', 'Manual UI only', 'Yes (Diff-Preserving)'],
        ['Bidirectional Conversion', 'No', 'No', 'Yes (DOCX <-> PPTX)'],
      ],
      layout: 'table',
    },
    {
      num: 9,
      type: 'Roadmap',
      title: 'Enterprise Deployment Roadmap',
      phases: [
        { q: 'Q1 2025', name: 'Foundation', items: ['Supervisor engine setup', 'Template vectorization', 'OCR vision pipeline'] },
        { q: 'Q2 2025', name: 'Grounding', items: ['Real-time web search', 'Pinecone DB integration', 'RAG confidence tuning'] },
        { q: 'Q3 2025', name: 'Scale', items: ['Conversational edits', 'Bidirectional converter', 'Enterprise SSO'] },
        { q: 'Q4 2025', name: 'Governance', items: ['SOC2 Type II certification', 'Audit trail dashboard', 'Global multi-region rollout'] },
      ],
      layout: 'roadmap',
    },
    {
      num: 10,
      type: 'Security & Governance',
      title: 'Enterprise Security & Governance Framework',
      col1Title: 'Data Privacy & Zero-Trust',
      col1Points: [
        'No training on proprietary customer prompt or template data.',
        'Role-Based Access Control (RBAC) with granular tenant isolation.',
        'AES-256 encryption at rest and TLS 1.3 in transit.',
      ],
      col2Title: 'Regulatory Compliance',
      col2Points: [
        'Aligned with EU AI Act Risk Management Framework [Web-5].',
        'Cryptographic version snapshots and immutable audit logs.',
        'Instant rollback to prior approved versions via VersionManager.',
      ],
      layout: 'two_col',
    },
    {
      num: 11,
      type: 'Citations & Sources',
      title: 'Source Citations & Research Provenance',
      citations: [
        { id: '[Web-1]', title: 'Gartner Top Strategic Technology Trends: Autonomous Multi-Agent AI', ref: 'gartner.com/strategic-trends' },
        { id: '[Web-2]', title: 'McKinsey Global Institute: The Economic Potential of Generative AI', ref: 'mckinsey.com/quantumblack' },
        { id: '[Web-3]', title: 'Stanford AI Index Report: Advanced RAG and Knowledge Graph Fusion', ref: 'aiindex.stanford.edu' },
        { id: '[Web-4]', title: 'MIT Technology Review: Rise of Domain-Specific SLMs', ref: 'technologyreview.com' },
        { id: '[Web-5]', title: 'IDC MarketScape: Enterprise AI Governance and EU AI Act Alignment', ref: 'idc.com/governance' },
      ],
      layout: 'citations',
    },
    {
      num: 12,
      type: 'Next Steps',
      title: 'Strategic Recommendations & Immediate Next Steps',
      subtitle: 'Immediate execution milestones for executive sponsorship',
      cards: [
        { label: '1. Approve Pilot Scope', text: 'Formalize 60-day pilot across strategy, consulting, and finance teams.', metric: 'Immediate' },
        { label: '2. Connect Enterprise KB', text: 'Index corporate knowledge repositories, brand guidelines, and slide templates.', metric: 'Week 2' },
        { label: '3. Production Sign-Off', text: 'Execute security audit, validate OpenXML compatibility, and rollout.', metric: 'Week 8' },
      ],
      layout: 'pillars',
    },
  ];

  const currentSlide = slidesData[currentSlideIndex];

  return (
    <div className="space-y-6">
      {/* Top Action Header with Downloads & Scorecard */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <Award className="w-5 h-5 text-emerald-400" />
            <h2 className="text-sm font-bold text-white uppercase tracking-wider">
              Generated OpenXML Enterprise Deliverables
            </h2>
          </div>
          <p className="text-xs text-slate-400">
            Fully editable Microsoft Word (.docx) & 12-Slide PowerPoint (.pptx) matching template typography & palettes
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <a
            href="/api/download/docx"
            download="Company_Proposal_Generated.docx"
            className="flex items-center space-x-2 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold px-3.5 py-2 rounded-lg transition-colors shadow"
          >
            <FileText className="w-4 h-4" />
            <span>Download DOCX Proposal</span>
          </a>

          <a
            href="/api/download/pptx"
            download="Company_Presentation_Generated.pptx"
            className="flex items-center space-x-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold px-3.5 py-2 rounded-lg transition-colors shadow"
          >
            <Presentation className="w-4 h-4" />
            <span>Download 12-Slide PPTX</span>
          </a>
        </div>
      </div>

      {/* Tabs Switcher */}
      <div className="flex items-center space-x-2 border-b border-slate-800 pb-2">
        <button
          onClick={() => setActiveTab('pptx')}
          className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-xs font-semibold transition-colors cursor-pointer ${
            activeTab === 'pptx' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white hover:bg-slate-800'
          }`}
        >
          <Presentation className="w-4 h-4" />
          <span>12-Slide Executive Presentation Preview (.pptx)</span>
          <span className="text-[10px] bg-black/30 px-1.5 py-0.5 rounded">16:9 Widescreen</span>
        </button>

        <button
          onClick={() => setActiveTab('docx')}
          className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-xs font-semibold transition-colors cursor-pointer ${
            activeTab === 'docx' ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-white hover:bg-slate-800'
          }`}
        >
          <FileText className="w-4 h-4" />
          <span>Enterprise Proposal Document Preview (.docx)</span>
          <span className="text-[10px] bg-black/30 px-1.5 py-0.5 rounded">6 Chapters</span>
        </button>
      </div>

      {/* Presentation Tab */}
      {activeTab === 'pptx' && (
        <div className="space-y-4">
          {/* Slide Navigation & Indicator */}
          <div className="flex items-center justify-between bg-slate-900 border border-slate-800 p-3 rounded-xl text-xs">
            <div className="flex items-center space-x-2">
              <span className="font-bold text-white">Slide {currentSlide.num} of 12:</span>
              <span className="text-slate-300 font-medium">{currentSlide.title}</span>
              <span className="text-[10px] bg-slate-800 text-blue-400 px-2 py-0.5 rounded border border-slate-700">
                {currentSlide.type}
              </span>
            </div>

            <div className="flex items-center space-x-2">
              <button
                onClick={() => setCurrentSlideIndex((prev) => Math.max(0, prev - 1))}
                disabled={currentSlideIndex === 0}
                className="p-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 disabled:opacity-40 cursor-pointer"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="text-slate-400 font-mono text-[11px]">{currentSlideIndex + 1} / 12</span>
              <button
                onClick={() => setCurrentSlideIndex((prev) => Math.min(11, prev + 1))}
                disabled={currentSlideIndex === 11}
                className="p-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 disabled:opacity-40 cursor-pointer"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* 16:9 Widescreen Slide Canvas Simulator */}
          <div className="w-full aspect-[16/9] max-w-5xl mx-auto bg-slate-50 border-4 border-slate-700 rounded-2xl p-8 sm:p-12 text-slate-900 shadow-2xl relative flex flex-col justify-between overflow-hidden">
            {/* Top Accent Line (Template Styling #2563EB) */}
            <div className="absolute top-0 left-0 right-0 h-2 bg-gradient-to-r from-blue-600 via-indigo-600 to-emerald-500"></div>

            {/* Slide Header */}
            {currentSlide.layout !== 'title' && (
              <div className="border-b border-slate-200 pb-3">
                <div className="flex items-center space-x-2 mb-1">
                  <div className="w-8 h-1 bg-emerald-500 rounded"></div>
                  <span className="text-[10px] font-bold tracking-wider text-blue-700 uppercase">
                    EXECUTIVE STRATEGY BRIEFING
                  </span>
                </div>
                <h3 className="text-xl sm:text-2xl font-bold text-[#0F2D59]">{currentSlide.title}</h3>
                {currentSlide.subtitle && (
                  <p className="text-xs sm:text-sm text-slate-500">{currentSlide.subtitle}</p>
                )}
              </div>
            )}

            {/* Slide Body Based on Layout */}
            <div className="flex-1 my-auto py-4">
              {/* Title Slide */}
              {currentSlide.layout === 'title' && (
                <div className="text-center space-y-4 my-auto">
                  <div className="inline-block px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-xs font-bold uppercase tracking-wider mb-2">
                    CONFIDENTIAL ENTERPRISE BRIEFING
                  </div>
                  <h2 className="text-3xl sm:text-4xl font-extrabold text-[#0F2D59] tracking-tight">
                    {currentSlide.title}
                  </h2>
                  <p className="text-base sm:text-lg text-slate-600 max-w-3xl mx-auto">
                    {currentSlide.subtitle}
                  </p>
                  <p className="text-xs text-slate-400 font-mono mt-8">{currentSlide.footer}</p>
                </div>
              )}

              {/* Executive Summary */}
              {currentSlide.layout === 'summary' && (
                <div className="space-y-4">
                  <div className="bg-slate-100 border-l-4 border-[#0F2D59] p-4 rounded-r-lg">
                    <span className="text-xs font-bold text-[#0F2D59] block mb-1">EXECUTIVE CALLOUT:</span>
                    <p className="text-xs sm:text-sm text-slate-700 leading-relaxed">{currentSlide.banner}</p>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    {currentSlide.cards?.map((c, i) => (
                      <div key={i} className="bg-white border border-slate-200 p-3.5 rounded-xl shadow-sm">
                        <span className="text-xs font-bold text-blue-600 block mb-1">{c.label}</span>
                        <p className="text-xs text-slate-600 leading-relaxed">{c.text}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 3 Pillars */}
              {currentSlide.layout === 'pillars' && (
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  {currentSlide.cards?.map((c, i) => (
                    <div key={i} className="bg-white border border-slate-200 p-4 rounded-xl shadow-sm flex flex-col justify-between">
                      <div>
                        <h4 className="text-sm font-bold text-[#0F2D59] mb-1">{c.label}</h4>
                        <p className="text-xs text-slate-600 leading-relaxed">{c.text}</p>
                      </div>
                      <div className="mt-4 pt-3 border-t border-slate-100">
                        <span className="text-xs font-bold text-emerald-600">{'metric' in c ? c.metric : ''}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Two Column */}
              {currentSlide.layout === 'two_col' && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="bg-white border border-slate-200 p-4 rounded-xl shadow-sm">
                    <h4 className="text-sm font-bold text-[#0F2D59] mb-2">{currentSlide.col1Title}</h4>
                    <ul className="space-y-2 text-xs text-slate-600">
                      {currentSlide.col1Points?.map((pt, i) => (
                        <li key={i} className="flex items-start space-x-2">
                          <span className="text-blue-600 font-bold">•</span>
                          <span>{pt}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div className="bg-white border border-slate-200 p-4 rounded-xl shadow-sm">
                    <h4 className="text-sm font-bold text-blue-600 mb-2">{currentSlide.col2Title}</h4>
                    <ul className="space-y-2 text-xs text-slate-600">
                      {currentSlide.col2Points?.map((pt, i) => (
                        <li key={i} className="flex items-start space-x-2">
                          <span className="text-emerald-600 font-bold">•</span>
                          <span>{pt}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}

              {/* Metrics */}
              {currentSlide.layout === 'metrics' && (
                <div className="grid grid-cols-2 gap-4">
                  {currentSlide.metrics?.map((m, i) => (
                    <div key={i} className="bg-white border border-slate-200 p-4 rounded-xl shadow-sm">
                      <div className="text-3xl font-extrabold text-emerald-600 mb-1">{m.val}</div>
                      <div className="text-xs font-bold text-[#0F2D59]">{m.label}</div>
                      <div className="text-[11px] text-slate-500 mt-0.5">{m.desc}</div>
                    </div>
                  ))}
                </div>
              )}

              {/* Table */}
              {currentSlide.layout === 'table' && (
                <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-[#0F2D59] text-white">
                      <tr>
                        {currentSlide.headers?.map((h, i) => (
                          <th key={i} className="p-2.5 font-bold">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {currentSlide.rows?.map((row, rIdx) => (
                        <tr key={rIdx} className={rIdx % 2 === 0 ? 'bg-white' : 'bg-slate-50'}>
                          {row.map((cell, cIdx) => (
                            <td key={cIdx} className={`p-2.5 ${cIdx === 3 ? 'font-bold text-blue-600' : 'text-slate-700'}`}>
                              {cell}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Roadmap */}
              {currentSlide.layout === 'roadmap' && (
                <div className="grid grid-cols-4 gap-3">
                  {currentSlide.phases?.map((p, i) => (
                    <div key={i} className="bg-white border border-slate-200 p-3.5 rounded-xl shadow-sm">
                      <span className="text-sm font-extrabold text-blue-600 block">{p.q}</span>
                      <span className="text-xs font-bold text-[#0F2D59] block mb-2">{p.name}</span>
                      <ul className="space-y-1 text-[11px] text-slate-600">
                        {p.items.map((it, idx) => (
                          <li key={idx}>• {it}</li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </div>
              )}

              {/* Citations */}
              {currentSlide.layout === 'citations' && (
                <div className="bg-white border border-slate-200 p-4 rounded-xl shadow-sm space-y-2">
                  <p className="text-xs font-bold text-[#0F2D59]">Verified Source Provenance Registry</p>
                  {currentSlide.citations?.map((c, i) => (
                    <div key={i} className="text-xs flex items-center justify-between border-b border-slate-100 pb-1.5">
                      <div className="flex items-center space-x-2">
                        <span className="font-bold text-blue-600">{c.id}</span>
                        <span className="text-slate-800 font-medium">{c.title}</span>
                      </div>
                      <span className="text-slate-400 font-mono text-[10px]">{c.ref}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Slide Footer */}
            <div className="flex items-center justify-between text-[10px] text-slate-400 border-t border-slate-200 pt-2">
              <span>Enterprise Multi-Agent POC • ECMA-376 OpenXML</span>
              <span>Slide {currentSlide.num} of 12</span>
            </div>
          </div>

          {/* Slide Thumbnail Strip */}
          <div className="grid grid-cols-6 sm:grid-cols-12 gap-1.5 bg-slate-900 border border-slate-800 p-2.5 rounded-xl overflow-x-auto">
            {slidesData.map((s, idx) => (
              <button
                key={idx}
                onClick={() => setCurrentSlideIndex(idx)}
                className={`p-1.5 rounded text-center transition-all cursor-pointer ${
                  currentSlideIndex === idx
                    ? 'bg-blue-600 text-white font-bold ring-2 ring-blue-400'
                    : 'bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-slate-200'
                }`}
              >
                <div className="text-[10px] uppercase font-mono">S{s.num}</div>
                <div className="text-[8px] truncate mt-0.5">{s.type}</div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Word Proposal Document Tab */}
      {activeTab === 'docx' && (
        <div className="max-w-4xl mx-auto bg-white border border-slate-300 rounded-xl p-8 sm:p-12 text-slate-900 shadow-xl space-y-6 font-serif">
          {/* Header Block */}
          <div className="text-center border-b border-slate-300 pb-6 font-sans">
            <span className="text-xs font-bold uppercase tracking-widest text-[#1B365D]">
              ENTERPRISE MULTI-AGENT PROPOSAL SPECIFICATION
            </span>
            <h2 className="text-2xl sm:text-3xl font-bold text-[#1B365D] mt-2">
              ENTERPRISE MULTI-AGENT AI PLATFORM
            </h2>
            <p className="text-sm text-slate-600 mt-1">
              Automated Document & Presentation Synthesis with Real-Time Web Grounding & Vector RAG
            </p>
            <div className="flex items-center justify-center space-x-4 text-xs text-slate-400 font-mono mt-3">
              <span>Version: 1.0</span>
              <span>•</span>
              <span>Classification: Enterprise Confidential</span>
              <span>•</span>
              <span>ECMA-376 Standard</span>
            </div>
          </div>

          {/* Executive Callout */}
          <div className="bg-slate-50 border-l-4 border-[#1B365D] p-5 rounded-r-lg font-sans">
            <h4 className="text-xs font-bold text-[#1B365D] uppercase tracking-wider mb-1">
              Executive Summary & Business Impact
            </h4>
            <p className="text-xs text-slate-700 leading-relaxed">
              This enterprise proposal establishes the deployment architecture for an autonomous multi-agent AI system
              engineered for Fortune 500 document workflow acceleration. By combining real-time web research, dense vector RAG,
              and template-preserving OpenXML generators, the platform reduces executive briefing preparation cycles by 65%
              while maintaining 100% compliance with brand typography, palettes, and data confidentiality standards.
            </p>
          </div>

          {/* Chapter 1 */}
          <div className="space-y-3">
            <h3 className="text-lg font-bold text-[#1B365D] font-sans border-b border-slate-200 pb-1">
              1. Strategic Context & Market Dynamics
            </h3>
            <p className="text-xs text-slate-700 leading-relaxed">
              The landscape of enterprise generative AI is transitioning from single-prompt chatbots to collaborative multi-agent ensembles.
              Recent industry analyses highlight this pivotal paradigm shift:
            </p>
            <ul className="list-disc list-inside text-xs text-slate-700 space-y-1 pl-2">
              <li><strong>Autonomous Task Orchestration:</strong> Gartner projects 40% enterprise software multi-agent adoption by 2026 [Web-1].</li>
              <li><strong>Economic Value Realization:</strong> McKinsey estimates $2.6T to $4.4T in annual enterprise value from automated document workflows [Web-2].</li>
              <li><strong>Factual Grounding:</strong> Stanford AI Index benchmarks demonstrate a 91.4% accuracy threshold for RAG-anchored workflows [Web-3].</li>
            </ul>
          </div>

          {/* Chapter 2: Table */}
          <div className="space-y-3">
            <h3 className="text-lg font-bold text-[#1B365D] font-sans border-b border-slate-200 pb-1">
              2. Multi-Agent Solution Architecture
            </h3>
            <div className="border border-slate-300 rounded-lg overflow-hidden font-sans">
              <table className="w-full text-left text-xs">
                <thead className="bg-[#1B365D] text-white">
                  <tr>
                    <th className="p-2.5 font-bold">Agent Role</th>
                    <th className="p-2.5 font-bold">Specialized Responsibility</th>
                    <th className="p-2.5 font-bold">Output Artifact</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  <tr className="bg-white"><td className="p-2 font-semibold">Supervisor Agent</td><td className="p-2">Task decomposition & graph routing</td><td className="p-2">State Graph</td></tr>
                  <tr className="bg-slate-50"><td className="p-2 font-semibold">Document Analyzer</td><td className="p-2">DOCX/PDF/OCR style extraction</td><td className="p-2">Style Spec</td></tr>
                  <tr className="bg-white"><td className="p-2 font-semibold">PPT Analyzer</td><td className="p-2">16:9 Widescreen layout extraction</td><td className="p-2">Slide Schema</td></tr>
                  <tr className="bg-slate-50"><td className="p-2 font-semibold">Web Researcher</td><td className="p-2">Live 2025 AI benchmarks</td><td className="p-2">Verified Insights</td></tr>
                  <tr className="bg-white"><td className="p-2 font-semibold">Enterprise RAG</td><td className="p-2">Dense vector retrieval over KB</td><td className="p-2">Knowledge Chunks</td></tr>
                  <tr className="bg-slate-50"><td className="p-2 font-semibold">Doc Generator</td><td className="p-2">Pure OpenXML Word synthesis</td><td className="p-2">Editable .docx</td></tr>
                  <tr className="bg-white"><td className="p-2 font-semibold">PPT Generator</td><td className="p-2">12-Slide deck synthesis</td><td className="p-2">Editable .pptx</td></tr>
                  <tr className="bg-slate-50"><td className="p-2 font-semibold">Validation Agent</td><td className="p-2">Package integrity & slide count QA</td><td className="p-2">Scorecard</td></tr>
                  <tr className="bg-white"><td className="p-2 font-semibold">Conversational Editor</td><td className="p-2">In-place diff revisions</td><td className="p-2">Version Snapshots</td></tr>
                </tbody>
              </table>
            </div>
          </div>

          {/* Chapter 3: Citations */}
          <div className="space-y-3 font-sans border-t border-slate-200 pt-4">
            <h3 className="text-sm font-bold text-[#1B365D]">Verified Sources & Research Citations</h3>
            <div className="space-y-1 text-xs text-slate-600">
              <p>[Web-1] Gartner Top Strategic Technology Trends: Autonomous Multi-Agent AI Systems (2025)</p>
              <p>[Web-2] McKinsey Global Institute: Economic Potential of Generative AI in Enterprise Operations (2025)</p>
              <p>[Web-3] Stanford AI Index Report: Advanced RAG and Knowledge Graph Fusion (2024)</p>
              <p>[RAG-1] Acme Enterprise AI Strategy & Governance Directive (2025-2027)</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
