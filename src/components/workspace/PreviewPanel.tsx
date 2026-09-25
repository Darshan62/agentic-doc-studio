import React, { useState } from 'react';
import {
  ChevronLeft, ChevronRight, Download, FileText, FolderOpen, Presentation, Redo2, Undo2, ZoomIn, ZoomOut,
} from 'lucide-react';

import { WorkspaceApi } from '../../workspace/useWorkspace';
import { DocumentPicker } from './DocumentPicker';
import { DocxPreview } from './DocxPreview';
import { PptxPreview } from './PptxPreview';

const ZOOM_STEPS = [0.5, 0.67, 0.8, 1, 1.25, 1.5, 2];

function ToolButton({ label, onClick, disabled, children }: {
  label: string; onClick: () => void; disabled?: boolean; children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      aria-label={label}
      title={label}
      className="p-1.5 rounded-md text-slate-300 hover:text-white hover:bg-slate-800 disabled:opacity-35 disabled:hover:bg-transparent cursor-pointer"
    >
      {children}
    </button>
  );
}

export const PreviewPanel: React.FC<{ ws: WorkspaceApi }> = ({ ws }) => {
  const [zoomIndex, setZoomIndex] = useState(3);
  const [picking, setPicking] = useState(false);
  const active = ws.state?.active ?? null;
  const preview = ws.state?.preview ?? null;
  const busy = ws.status !== 'idle';

  if (!active || !preview || picking) {
    return (
      <div className="h-full overflow-y-auto bg-slate-950">
        {picking && active && (
          <button onClick={() => setPicking(false)} className="m-4 text-xs text-slate-400 hover:text-white cursor-pointer">
            ← Back to {active.name}
          </button>
        )}
        <DocumentPicker
          artifacts={ws.artifacts}
          busy={busy}
          onOpen={(p) => { setPicking(false); ws.open(p); }}
          onUpload={(f) => { setPicking(false); ws.upload(f); }}
        />
      </div>
    );
  }

  const zoom = ZOOM_STEPS[zoomIndex];
  const isPptx = preview.type === 'pptx';
  const slideCount = preview.type === 'pptx' ? preview.slides.length : 0;
  const TypeIcon = isPptx ? Presentation : FileText;

  return (
    <div className="flex flex-col h-full min-h-0 bg-slate-950">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2 px-3 py-2 border-b border-slate-800 bg-slate-900">
        <div className="flex items-center gap-2 min-w-0 flex-1">
          <TypeIcon className={`w-4 h-4 flex-shrink-0 ${isPptx ? 'text-orange-400' : 'text-blue-400'}`} aria-hidden />
          <span className="text-sm text-white font-medium truncate" title={active.name}>{active.name}</span>
          <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${isPptx ? 'bg-orange-500/20 text-orange-300' : 'bg-blue-500/20 text-blue-300'}`}>
            {active.type.toUpperCase()}
          </span>
          <select
            value={active.version}
            onChange={(e) => ws.restore(e.target.value)}
            disabled={busy}
            aria-label="Version"
            className="min-w-0 max-w-[45vw] sm:max-w-xs bg-slate-800 border border-slate-700 text-amber-300 font-mono text-xs rounded px-1.5 py-0.5 cursor-pointer truncate"
          >
            {[...(ws.state?.versions ?? [])].reverse().map((v) => (
              <option key={v.version} value={v.version}>
                {v.version} — {v.instruction.length > 40 ? `${v.instruction.slice(0, 38)}…` : v.instruction}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-0.5">
          <ToolButton label="Undo" onClick={ws.undo} disabled={busy || !active.can_undo}><Undo2 className="w-4 h-4" /></ToolButton>
          <ToolButton label="Redo" onClick={ws.redo} disabled={busy || !active.can_redo}><Redo2 className="w-4 h-4" /></ToolButton>
          <span className="w-px h-5 bg-slate-700 mx-1" />
          <ToolButton label="Zoom out" onClick={() => setZoomIndex((i) => Math.max(0, i - 1))} disabled={zoomIndex === 0}>
            <ZoomOut className="w-4 h-4" />
          </ToolButton>
          <span className="text-xs text-slate-400 w-10 text-center tabular-nums">{Math.round(zoom * 100)}%</span>
          <ToolButton label="Zoom in" onClick={() => setZoomIndex((i) => Math.min(ZOOM_STEPS.length - 1, i + 1))} disabled={zoomIndex === ZOOM_STEPS.length - 1}>
            <ZoomIn className="w-4 h-4" />
          </ToolButton>
          {isPptx && (
            <>
              <span className="w-px h-5 bg-slate-700 mx-1" />
              <ToolButton label="Previous slide" onClick={() => ws.setCurrentSlide(ws.currentSlide - 1)} disabled={ws.currentSlide <= 1}>
                <ChevronLeft className="w-4 h-4" />
              </ToolButton>
              <span className="text-xs text-slate-300 tabular-nums">{Math.min(ws.currentSlide, slideCount)} / {slideCount}</span>
              <ToolButton label="Next slide" onClick={() => ws.setCurrentSlide(ws.currentSlide + 1)} disabled={ws.currentSlide >= slideCount}>
                <ChevronRight className="w-4 h-4" />
              </ToolButton>
            </>
          )}
          <span className="w-px h-5 bg-slate-700 mx-1" />
          <ToolButton label="Open another document" onClick={() => setPicking(true)} disabled={busy}><FolderOpen className="w-4 h-4" /></ToolButton>
          <a
            href={`/api/workspace/download?v=${encodeURIComponent(active.version)}`}
            download={active.name}
            className="ml-1 inline-flex items-center gap-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold px-3 py-1.5 rounded-md"
          >
            <Download className="w-3.5 h-3.5" aria-hidden /> Download
          </a>
        </div>
      </div>

      {/* Document */}
      <div className="flex-1 min-h-0 overflow-auto bg-slate-800/60" key={active.version}>
        {preview.type === 'docx' ? (
          <DocxPreview model={preview} zoom={zoom} selection={ws.selection} onSelect={ws.setSelection} />
        ) : (
          <PptxPreview model={preview} zoom={zoom} currentSlide={ws.currentSlide} onSlideChange={ws.setCurrentSlide}
            selection={ws.selection} onSelect={ws.setSelection} />
        )}
      </div>
    </div>
  );
};
