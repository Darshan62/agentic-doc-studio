import React, { useRef } from 'react';
import { FileText, Presentation, Upload } from 'lucide-react';

import { ArtifactFile } from '../../workspace/types';

interface DocumentPickerProps {
  artifacts: ArtifactFile[];
  onOpen: (path: string) => void;
  onUpload: (file: File) => void;
  busy: boolean;
}

export const DocumentPicker: React.FC<DocumentPickerProps> = ({ artifacts, onOpen, onUpload, busy }) => {
  const fileRef = useRef<HTMLInputElement>(null);
  const groups = artifacts.reduce<Record<string, ArtifactFile[]>>((acc, item) => {
    (acc[item.group] ??= []).push(item);
    return acc;
  }, {});

  return (
    <div className="max-w-2xl mx-auto w-full p-6 space-y-5">
      <div>
        <h2 className="text-lg font-semibold text-white">Open a document to edit</h2>
        <p className="text-sm text-slate-400">
          The editor works on a copy: your original file is never changed. Every edit becomes a new version you can undo.
        </p>
      </div>

      <button
        onClick={() => fileRef.current?.click()}
        disabled={busy}
        className="w-full border-2 border-dashed border-slate-700 hover:border-blue-500 rounded-xl py-6 flex flex-col items-center gap-2 text-slate-300 cursor-pointer disabled:opacity-50"
      >
        <Upload className="w-6 h-6 text-blue-400" aria-hidden />
        <span className="text-sm font-medium">Upload a .docx or .pptx</span>
        <span className="text-xs text-slate-500">or pick one below</span>
      </button>
      <input
        ref={fileRef}
        type="file"
        accept=".docx,.pptx"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          e.target.value = '';
          if (file) onUpload(file);
        }}
      />

      {Object.entries(groups).map(([group, items]) => (
        <section key={group}>
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">{group}</h3>
          <ul className="grid sm:grid-cols-2 gap-2">
            {items.map((item) => {
              const Icon = item.type === 'pptx' ? Presentation : FileText;
              return (
                <li key={item.path}>
                  <button
                    onClick={() => onOpen(item.path)}
                    disabled={busy}
                    className="w-full flex items-center gap-3 text-left bg-slate-800/70 hover:bg-slate-800 border border-slate-700 hover:border-blue-500 rounded-lg p-3 cursor-pointer disabled:opacity-50"
                  >
                    <Icon className={`w-6 h-6 flex-shrink-0 ${item.type === 'pptx' ? 'text-orange-400' : 'text-blue-400'}`} aria-hidden />
                    <span className="min-w-0">
                      <span className="block text-sm text-white truncate">{item.name}</span>
                      <span className="block text-[11px] text-slate-400 uppercase">{item.type}</span>
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        </section>
      ))}
    </div>
  );
};
