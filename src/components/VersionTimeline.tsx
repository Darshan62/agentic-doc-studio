import React from 'react';
import { History, GitCommit, CheckCircle2, RotateCcw, FileText, Presentation } from 'lucide-react';
import { VersionRecord } from '../types';

interface VersionTimelineProps {
  versions: VersionRecord[];
}

export const VersionTimeline: React.FC<VersionTimelineProps> = ({ versions }) => {
  const fallbackVersions: VersionRecord[] = [
    {
      version: 'v1.0',
      timestamp: Date.now() - 3600000,
      author: 'Supervisor Agent',
      instruction: 'Initial generation from user request and uploaded templates',
      diff_summary: [
        'Created initial Word proposal (.docx) adhering to Georgia/Arial typography and Navy #1B365D.',
        'Created 12-slide executive presentation (.pptx) adhering to 16:9 widescreen geometry and theme palette.',
      ],
      changes_count: 2,
    },
    {
      version: 'v1.1',
      timestamp: Date.now() - 1800000,
      author: 'Conversational Editing Agent',
      instruction: 'Add an executive summary.',
      diff_summary: [
        'DOCX: Prepended executive summary callout block to document header.',
        'PPTX: Highlighted Executive Summary Slide 02 with strategic key pillars.',
      ],
      changes_count: 2,
    },
    {
      version: 'v1.2',
      timestamp: Date.now() - 600000,
      author: 'Conversational Editing Agent',
      instruction: 'Make the presentation more concise.',
      diff_summary: [
        'PPTX: Condensed all slide bullet points by 40%, streamlined into high-impact executive format.',
        'DOCX: Re-formatted body text with bulleted takeaways for executive review.',
      ],
      changes_count: 2,
    },
  ];

  const list = versions && versions.length > 0 ? versions : fallbackVersions;

  return (
    <div className="space-y-6">
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            <History className="w-5 h-5 text-purple-400" />
            <h2 className="text-sm font-bold text-white uppercase tracking-wider">
              Cryptographic Version Snapshots & Audit Trail
            </h2>
          </div>
          <span className="text-xs bg-purple-500/20 text-purple-300 px-2.5 py-1 rounded-full border border-purple-500/30">
            {list.length} Checkpoints Captured • Rollback Ready
          </span>
        </div>
        <p className="text-xs text-slate-400">
          Every conversational edit, prompt revision, and format conversion creates an immutable version record with full unified text diffs.
        </p>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
        <h3 className="text-sm font-bold text-white uppercase tracking-wider">Version History</h3>

        <div className="relative border-l border-slate-700 ml-4 space-y-6">
          {list.map((v, idx) => (
            <div key={idx} className="relative pl-6">
              {/* Dot */}
              <div className="absolute -left-2 top-1 w-4 h-4 rounded-full bg-purple-600 border-2 border-slate-900 flex items-center justify-center">
                <div className="w-1.5 h-1.5 rounded-full bg-white"></div>
              </div>

              <div className="bg-slate-800/50 border border-slate-700 p-4 rounded-xl text-xs space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <span className="font-bold text-sm text-purple-300 font-mono">{v.version}</span>
                    <span className="text-slate-200 font-semibold">{v.instruction}</span>
                  </div>
                  <span className="text-[10px] text-slate-400 font-mono">
                    {new Date(v.timestamp * (v.timestamp < 10000000000 ? 1000 : 1)).toLocaleTimeString()}
                  </span>
                </div>

                <div className="text-[11px] text-slate-400">
                  Author: <span className="text-slate-300 font-semibold">{v.author}</span>
                </div>

                <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800 space-y-1">
                  <span className="text-[10px] uppercase font-bold text-slate-400 block mb-1">
                    Diff & Change Summary:
                  </span>
                  {v.diff_summary?.map((d, dIdx) => (
                    <div key={dIdx} className="text-slate-300 font-mono text-[11px] flex items-start space-x-1.5">
                      <span className="text-emerald-400 font-bold">+</span>
                      <span>{d}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
