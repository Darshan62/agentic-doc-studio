import React, { useState } from 'react';
import { Download, FileText, Presentation, ChevronLeft, ChevronRight } from 'lucide-react';

import { DeckSlide, GeneratedContent, OrchestrationResult, ValidationScorecard } from '../types';

interface ArtifactViewerProps {
  result: OrchestrationResult | null;
}

function BulletList({ items }: { items?: string[] }) {
  if (!items?.length) return null;
  return (
    <ul className="list-disc pl-5 space-y-1 text-sm text-slate-700">
      {items.map((item, i) => <li key={i}>{item}</li>)}
    </ul>
  );
}

function Table({ headers, rows }: { headers?: string[]; rows?: string[][] }) {
  if (!headers?.length) return null;
  return (
    <table className="w-full text-xs border border-slate-300 my-2">
      <thead className="bg-slate-800 text-white">
        <tr>{headers.map((h, i) => <th key={i} className="p-2 text-left">{h}</th>)}</tr>
      </thead>
      <tbody>
        {rows?.map((row, r) => (
          <tr key={r} className="border-t border-slate-200">
            {row.map((cell, c) => <td key={c} className="p-2 text-slate-700">{cell}</td>)}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

// Renders one slide body; mirrors the layouts in agents/ppt_generator.py
function SlideBody({ slide }: { slide: DeckSlide }) {
  switch (slide.layout) {
    case 'two_column':
      return (
        <div className="grid grid-cols-2 gap-4">
          <div><h4 className="font-bold text-sm mb-1 text-slate-800">{slide.left_title}</h4><BulletList items={slide.left_points} /></div>
          <div><h4 className="font-bold text-sm mb-1 text-slate-800">{slide.right_title}</h4><BulletList items={slide.right_points} /></div>
        </div>
      );
    case 'three_pillar':
      return (
        <div className="grid grid-cols-3 gap-3">
          {slide.pillars?.map((p, i) => (
            <div key={i} className="border border-slate-200 rounded-lg p-3">
              <p className="font-bold text-sm text-slate-800">{p.title}</p>
              <p className="text-xs text-slate-600 my-1">{p.desc}</p>
              <p className="text-xs font-bold text-blue-700">{p.metric}</p>
            </div>
          ))}
        </div>
      );
    case 'metrics':
      return (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {slide.metrics?.map((m, i) => (
            <div key={i} className="border border-slate-200 rounded-lg p-3 text-center">
              <p className="text-2xl font-bold text-blue-700">{m.value}</p>
              <p className="text-xs font-bold text-slate-800">{m.label}</p>
              <p className="text-[11px] text-slate-500">{m.desc}</p>
            </div>
          ))}
        </div>
      );
    case 'table':
      return <Table headers={slide.headers} rows={slide.rows} />;
    default:
      return (
        <div className="space-y-2">
          {slide.summary && <p className="text-sm text-slate-700 bg-slate-100 p-3 rounded">{slide.summary}</p>}
          <BulletList items={slide.points} />
        </div>
      );
  }
}

function SlidePreview({ content }: { content: GeneratedContent }) {
  const [index, setIndex] = useState(0);
  const slides = content.deck.slides;
  const slide = slides[Math.min(index, slides.length - 1)];

  return (
    <div>
      <div className="bg-white rounded-xl aspect-video p-6 overflow-auto shadow-inner">
        <h3 className="text-xl font-bold text-slate-900 mb-4">{slide.title}</h3>
        <SlideBody slide={slide} />
      </div>
      <div className="flex items-center justify-between mt-3 text-xs text-slate-300">
        <button onClick={() => setIndex((i) => Math.max(0, i - 1))} disabled={index === 0}
          className="flex items-center gap-1 disabled:opacity-30 cursor-pointer" aria-label="Previous slide">
          <ChevronLeft className="w-4 h-4" /> Prev
        </button>
        <span>Content slide {index + 1} of {slides.length} (the file also has a title and a sources slide)</span>
        <button onClick={() => setIndex((i) => Math.min(slides.length - 1, i + 1))} disabled={index >= slides.length - 1}
          className="flex items-center gap-1 disabled:opacity-30 cursor-pointer" aria-label="Next slide">
          Next <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}

function DocumentPreview({ content }: { content: GeneratedContent }) {
  const doc = content.document;
  return (
    <article className="bg-white rounded-xl p-8 max-h-[70vh] overflow-auto space-y-4">
      <h2 className="text-2xl font-bold text-slate-900">{doc.title}</h2>
      {doc.subtitle && <p className="text-slate-500">{doc.subtitle}</p>}
      {doc.executive_summary && (
        <div className="border-l-4 border-blue-800 bg-slate-100 p-4 text-sm text-slate-700">
          <p className="font-bold mb-1">Executive Summary</p>
          {doc.executive_summary}
        </div>
      )}
      {doc.sections.map((section, i) => (
        <section key={i} className="space-y-2">
          <h3 className="text-lg font-bold text-slate-900">{i + 1}. {section.heading}</h3>
          {section.paragraphs.map((p, j) => <p key={j} className="text-sm text-slate-700">{p}</p>)}
          <BulletList items={section.bullets} />
          {section.table && <Table headers={section.table.headers} rows={section.table.rows} />}
        </section>
      ))}
    </article>
  );
}

function ValidationBadge({ card }: { card: ValidationScorecard }) {
  const passed = card.status === 'PASSED';
  return (
    <span className={`text-xs px-2.5 py-1 rounded-full border ${passed ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30' : 'bg-red-500/20 text-red-300 border-red-500/30'}`}>
      {card.artifact} {card.status} ({card.quality_score}%)
    </span>
  );
}

export const ArtifactViewer: React.FC<ArtifactViewerProps> = ({ result }) => {
  const [activeTab, setActiveTab] = useState<'pptx' | 'docx'>('pptx');

  if (!result) {
    return (
      <p className="bg-slate-900 border border-dashed border-slate-800 rounded-xl p-10 text-center text-sm text-slate-400">
        Nothing generated yet. Go to the chat tab and press <b>Generate new</b>.
      </p>
    );
  }

  const tabClass = (tab: string) =>
    `flex items-center gap-2 text-xs px-3 py-2 rounded-lg cursor-pointer ${activeTab === tab ? 'bg-blue-600 text-white' : 'bg-slate-800 text-slate-300'}`;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex gap-2">
          <button className={tabClass('pptx')} onClick={() => setActiveTab('pptx')}><Presentation className="w-4 h-4" /> Slides</button>
          <button className={tabClass('docx')} onClick={() => setActiveTab('docx')}><FileText className="w-4 h-4" /> Document</button>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <ValidationBadge card={result.validation.pptx} />
          <ValidationBadge card={result.validation.docx} />
          <a href={`/api/download/${activeTab}`} download
            className="flex items-center gap-1.5 text-xs bg-emerald-600 hover:bg-emerald-500 text-white px-3 py-2 rounded-lg">
            <Download className="w-4 h-4" /> Download .{activeTab}
          </a>
        </div>
      </div>

      {activeTab === 'pptx' ? <SlidePreview content={result.content} /> : <DocumentPreview content={result.content} />}
    </div>
  );
};
