import React from 'react';
import { ShieldCheck, Globe, Database, ExternalLink } from 'lucide-react';

import { Citation, GeneratedContent } from '../types';

interface TraceabilityMatrixProps {
  citations: Citation[];
  content: GeneratedContent | null;
}

// Lists the document sections and slides whose text mentions this citation id, e.g. "[Web-1]"
function findCitedLocations(citationId: string, content: GeneratedContent): string[] {
  const sections = content.document.sections
    .filter((s) => JSON.stringify(s).includes(citationId))
    .map((s) => `Doc: ${s.heading}`);
  const slides = content.deck.slides
    .map((slide, i) => ({ slide, number: i + 2 })) // +2: slide 1 is the title slide
    .filter(({ slide }) => JSON.stringify(slide).includes(citationId))
    .map(({ slide, number }) => `Slide ${number}: ${slide.title}`);
  return [...sections, ...slides];
}

export const TraceabilityMatrix: React.FC<TraceabilityMatrixProps> = ({ citations, content }) => {
  if (!content || citations.length === 0) {
    return (
      <p className="bg-slate-900 border border-dashed border-slate-800 rounded-xl p-10 text-center text-sm text-slate-400">
        No sources yet. Generate a proposal first.
      </p>
    );
  }

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
      <div className="flex items-center space-x-2">
        <ShieldCheck className="w-5 h-5 text-emerald-400" />
        <h2 className="text-sm font-bold text-white uppercase tracking-wider">Sources & Where They Are Cited ({citations.length})</h2>
      </div>
      <p className="text-xs text-slate-400">
        Web sources come from Gemini's Google Search. Knowledge sources are chunks retrieved from the sample files and your uploads.
      </p>

      <div className="space-y-3">
        {citations.map((c) => {
          const locations = findCitedLocations(c.id, content);
          const isWeb = c.source_type === 'web';
          return (
            <div key={c.id} className="bg-slate-800/40 border border-slate-700/60 rounded-lg p-3 text-xs space-y-1.5">
              <div className="flex items-center gap-2">
                {isWeb ? <Globe className="w-4 h-4 text-sky-400" /> : <Database className="w-4 h-4 text-violet-400" />}
                <span className="font-mono font-bold text-slate-200">{c.id}</span>
                <span className="text-slate-200 truncate">{c.title}</span>
              </div>
              {isWeb ? (
                <a href={c.reference} target="_blank" rel="noreferrer" className="text-sky-300 hover:underline inline-flex items-center gap-1">
                  Open source <ExternalLink className="w-3 h-3" />
                </a>
              ) : (
                <p className="text-slate-400">From {c.reference} (similarity {Math.round(c.confidence * 100)}%)</p>
              )}
              <p className={locations.length ? 'text-emerald-300' : 'text-amber-300'}>
                {locations.length ? `Cited in: ${locations.join(' • ')}` : 'Retrieved but not cited in the text'}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
};
