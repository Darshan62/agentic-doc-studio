import React from 'react';
import { History, GitCommit } from 'lucide-react';

import { VersionRecord } from '../types';

interface VersionTimelineProps {
  versions: VersionRecord[];
}

export const VersionTimeline: React.FC<VersionTimelineProps> = ({ versions }) => {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
      <div className="flex items-center space-x-2">
        <History className="w-5 h-5 text-amber-400" />
        <h2 className="text-sm font-bold text-white uppercase tracking-wider">Version History ({versions.length})</h2>
      </div>
      <p className="text-xs text-slate-400">
        Each generation and edit copies the .docx and .pptx into <code>versions/&lt;version&gt;/</code>.
      </p>

      {versions.length === 0 ? (
        <p className="text-xs text-slate-400 text-center py-8 border border-dashed border-slate-800 rounded-lg">
          No versions yet. Generate a proposal first.
        </p>
      ) : (
        <ol className="space-y-3">
          {[...versions].reverse().map((v) => (
            <li key={v.version} className="bg-slate-800/40 border border-slate-700/60 rounded-lg p-3 text-xs space-y-1">
              <div className="flex items-center gap-2">
                <GitCommit className="w-4 h-4 text-amber-400" />
                <span className="font-mono font-bold text-amber-300">{v.version}</span>
                <span className="text-slate-300">{v.author}</span>
                <span className="text-slate-500 ml-auto">{new Date(v.timestamp * 1000).toLocaleString()}</span>
              </div>
              <p className="text-slate-200">"{v.instruction}"</p>
              <ul className="list-disc pl-5 text-slate-400">
                {v.diff_summary.map((change, i) => <li key={i}>{change}</li>)}
              </ul>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
};
