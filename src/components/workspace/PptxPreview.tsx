import React, { useEffect, useRef, useState } from 'react';

import { PptxPreviewModel, Selection, SlideModel, SlideShape } from '../../workspace/types';

const EMU_PER_POINT = 12700;
const THUMB_WIDTH = 132;

interface PptxPreviewProps {
  model: PptxPreviewModel;
  zoom: number;
  currentSlide: number;
  onSlideChange: (n: number) => void;
  selection: Selection | null;
  onSelect: (selection: Selection | null) => void;
}

const ALIGN: Record<string, React.CSSProperties['textAlign']> = { l: 'left', ctr: 'center', r: 'right', just: 'justify' };
const ANCHOR: Record<string, string> = { t: 'flex-start', ctr: 'center', b: 'flex-end' };

function fontFamily(font: string | null): string | undefined {
  return font ? `"${font.replace(/["\\;]/g, '')}", Arial, sans-serif` : undefined;
}

function ShapeView({ shape, model, pxPerPt, slide, interactive, selection, onSelect }: {
  shape: SlideShape; model: PptxPreviewModel; pxPerPt: number; slide: number; interactive: boolean;
  selection: Selection | null; onSelect: (s: Selection | null) => void;
}) {
  const isSelected = interactive && selection !== null && 'shape_id' in selection && selection.slide === slide && selection.shape_id === shape.id;
  const selectable = interactive && (shape.kind === 'text' || shape.kind === 'picture');
  const box: React.CSSProperties = {
    position: 'absolute',
    left: `${(shape.x / model.width) * 100}%`,
    top: `${(shape.y / model.height) * 100}%`,
    width: `${(shape.cx / model.width) * 100}%`,
    height: `${(shape.cy / model.height) * 100}%`,
  };
  const ring = isSelected ? 'outline outline-2 outline-blue-500 z-20' : shape.changed && interactive ? 'ws-flash z-10' : selectable ? 'hover:outline hover:outline-1 hover:outline-blue-400' : '';
  const select = (e: React.MouseEvent) => {
    if (!selectable) return;
    e.stopPropagation();
    const what = shape.kind === 'picture' ? (shape.is_logo ? 'the logo' : 'a picture') : `“${(shape.paragraphs?.[0]?.runs[0]?.text ?? shape.name).slice(0, 24)}”`;
    onSelect(isSelected ? null : { kind: shape.kind === 'picture' ? 'image' : 'shape', slide, shape_id: shape.id, label: `${what} on slide ${slide}` });
  };

  if (shape.kind === 'picture') {
    const src = shape.media ? model.media[shape.media] : undefined;
    return (
      <div style={box} className={`${ring} ${selectable ? 'cursor-pointer' : ''}`} onClick={select}>
        {src ? <img src={src} alt={shape.name} className="w-full h-full" draggable={false} /> : <div className="w-full h-full bg-slate-200" />}
      </div>
    );
  }
  const inset = (shape.inset ?? [91440, 45720, 91440, 45720]).map((v) => (v / EMU_PER_POINT) * pxPerPt);
  const radius = shape.geometry === 'ellipse' ? '50%' : shape.geometry === 'roundRect' ? `${Math.min(shape.cx, shape.cy) / EMU_PER_POINT * pxPerPt * 0.1}px` : 0;
  return (
    <div
      style={{
        ...box,
        background: shape.fill ?? undefined,
        border: shape.line ? `${Math.max(1, ((shape.line_width ?? 12700) / EMU_PER_POINT) * pxPerPt)}px solid ${shape.line}` : undefined,
        borderRadius: radius,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: ANCHOR[shape.anchor ?? 't'] ?? 'flex-start',
        padding: `${inset[1]}px ${inset[2]}px ${inset[3]}px ${inset[0]}px`,
        overflow: 'hidden',
      }}
      className={`${ring} ${selectable ? 'cursor-pointer' : ''}`}
      onClick={select}
    >
      {shape.paragraphs?.map((p, i) => (
        <div
          key={i}
          style={{
            textAlign: ALIGN[p.align] ?? 'left',
            paddingLeft: p.bullet ? `${(18 + p.level * 18) * pxPerPt}px` : undefined,
            textIndent: p.bullet ? `${-14 * pxPerPt}px` : undefined,
            marginTop: `${p.space_before * pxPerPt}px`,
            minHeight: `${p.size * 1.2 * pxPerPt}px`,
            lineHeight: 1.2,
            whiteSpace: 'pre-wrap',
            overflowWrap: 'break-word',
          }}
        >
          {p.bullet && (
            <span style={{ fontSize: `${(p.runs[0]?.size ?? p.size) * pxPerPt}px`, color: p.runs[0]?.color ?? undefined, display: 'inline-block', width: `${14 * pxPerPt}px`, textIndent: 0 }}>
              {p.bullet}
            </span>
          )}
          {p.runs.map((r, j) => (
            <span
              key={j}
              style={{
                fontFamily: fontFamily(r.font),
                fontSize: `${r.size * pxPerPt}px`,
                fontWeight: r.bold ? 700 : 400,
                fontStyle: r.italic ? 'italic' : 'normal',
                textDecoration: r.underline ? 'underline' : undefined,
                color: r.color ?? '#000000',
              }}
            >
              {r.text}
            </span>
          ))}
        </div>
      ))}
    </div>
  );
}

function SlideCanvas({ slide, model, width, interactive, selection, onSelect }: {
  slide: SlideModel; model: PptxPreviewModel; width: number; interactive: boolean;
  selection: Selection | null; onSelect: (s: Selection | null) => void;
}) {
  const pxPerPt = width / (model.width / EMU_PER_POINT);
  return (
    <div
      className="relative overflow-hidden shadow-xl shadow-black/30 select-none"
      style={{ width, height: (width * model.height) / model.width, background: slide.background }}
      onClick={() => interactive && onSelect(null)}
    >
      {slide.shapes.map((shape) => (
        <ShapeView key={shape.id} shape={shape} model={model} pxPerPt={pxPerPt} slide={slide.index}
          interactive={interactive} selection={selection} onSelect={onSelect} />
      ))}
    </div>
  );
}

export const PptxPreview: React.FC<PptxPreviewProps> = ({ model, zoom, currentSlide, onSlideChange, selection, onSelect }) => {
  const frameRef = useRef<HTMLDivElement>(null);
  const [frameWidth, setFrameWidth] = useState(800);

  useEffect(() => {
    const frame = frameRef.current;
    if (!frame) return;
    const observer = new ResizeObserver(([entry]) => setFrameWidth(entry.contentRect.width));
    observer.observe(frame);
    return () => observer.disconnect();
  }, []);

  const slide = model.slides[Math.min(currentSlide, model.slides.length) - 1];
  if (!slide) return <p className="p-6 text-sm text-slate-400">This presentation has no slides.</p>;
  const width = Math.max(240, (frameWidth - 48) * zoom);

  return (
    <div className="flex flex-col h-full min-h-0">
      <div ref={frameRef} className="flex-1 min-h-0 overflow-auto">
        <div className="p-6 min-w-fit flex justify-center">
          <SlideCanvas slide={slide} model={model} width={width} interactive selection={selection} onSelect={onSelect} />
        </div>
      </div>
      <div className="border-t border-slate-800 bg-slate-900/80 px-3 py-2 flex gap-2 overflow-x-auto" role="tablist" aria-label="Slides">
        {model.slides.map((s) => (
          <button
            key={s.index}
            role="tab"
            aria-selected={s.index === slide.index}
            onClick={() => onSlideChange(s.index)}
            className={`flex-shrink-0 text-left rounded-md p-1 cursor-pointer border-2 ${s.index === slide.index ? 'border-blue-500' : 'border-transparent hover:border-slate-600'} ${s.changed ? 'ws-flash' : ''}`}
            title={s.title}
          >
            <div className="pointer-events-none">
              <SlideCanvas slide={s} model={model} width={THUMB_WIDTH} interactive={false} selection={null} onSelect={() => undefined} />
            </div>
            <span className="block text-[10px] text-slate-400 mt-1 truncate" style={{ width: THUMB_WIDTH }}>
              {s.index}. {s.title || 'Untitled'}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
};
