import React from 'react';

import { DocxItem, DocxParagraph, DocxPreviewModel, DocxTable, Selection } from '../../workspace/types';

const TWIPS_PER_PX = 15; // 1440 twips per inch, 96 px per inch

interface DocxPreviewProps {
  model: DocxPreviewModel;
  zoom: number;
  selection: Selection | null;
  onSelect: (selection: Selection | null) => void;
}

function fontFamily(font: string | null): string | undefined {
  return font ? `"${font.replace(/["\\;]/g, '')}", Arial, sans-serif` : undefined;
}

function Item({ item, model, selected, onSelect }: {
  item: DocxItem; model: DocxPreviewModel; selected: boolean; onSelect: (s: Selection) => void;
}) {
  if ('image' in item) {
    const src = item.media ? model.media[item.media] : undefined;
    const ring = selected ? 'ring-2 ring-blue-500' : item.changed ? 'ws-flash ring-2 ring-amber-400' : 'hover:ring-2 hover:ring-blue-300';
    const label = item.name ? `image ${item.image} (${item.name})` : `image ${item.image}`;
    return src ? (
      <img
        src={src}
        alt={item.name || `Image ${item.image}`}
        width={item.width}
        height={item.height}
        onClick={(e) => { e.stopPropagation(); onSelect({ kind: 'image', index: item.image, label }); }}
        className={`inline-block align-middle cursor-pointer rounded-sm ${ring}`}
        style={{ width: item.width, height: item.height }}
      />
    ) : (
      <span className="inline-block bg-slate-200 text-slate-500 text-xs px-2 py-1 rounded">[image {item.image}]</span>
    );
  }
  return (
    <span
      style={{
        fontFamily: fontFamily(item.font),
        fontSize: `${item.size}pt`,
        fontWeight: item.bold ? 700 : 400,
        fontStyle: item.italic ? 'italic' : 'normal',
        textDecoration: item.underline ? 'underline' : undefined,
        color: item.color ?? '#000000',
      }}
    >
      {item.text}
    </span>
  );
}

function Paragraph({ p, model, selection, onSelect }: {
  p: DocxParagraph; model: DocxPreviewModel; selection: Selection | null; onSelect: (s: Selection | null) => void;
}) {
  const isSelected = selection?.kind === 'paragraph' && selection.pid === p.pid && p.pid !== null;
  const isHeading = p.role === 'heading' || p.role === 'title';
  const selectable = p.pid !== null;
  const state = isSelected
    ? 'bg-blue-50 outline outline-2 outline-blue-500'
    : p.changed ? 'ws-flash' : selectable ? 'hover:outline hover:outline-1 hover:outline-blue-300' : '';
  const firstText = p.items.find((i) => 'text' in i && i.text.trim()) as { text: string } | undefined;
  return (
    <div
      className={`group relative rounded-sm ${selectable ? 'cursor-pointer' : ''} ${state}`}
      style={{
        textAlign: (p.align === 'both' ? 'justify' : p.align ?? 'left') as React.CSSProperties['textAlign'],
        marginTop: isHeading ? '14pt' : 0,
        marginBottom: '6pt',
        minHeight: `${p.size * 1.15}pt`,
        lineHeight: 1.3,
        whiteSpace: 'pre-wrap',
        paddingLeft: p.list ? '18pt' : undefined,
      }}
      onClick={(e) => {
        e.stopPropagation();
        if (!selectable) return;
        onSelect(isSelected ? null : { kind: 'paragraph', pid: p.pid as number, label: `¶${p.pid} “${(firstText?.text ?? '').slice(0, 28)}…”` });
      }}
    >
      {selectable && (
        <span className="absolute -left-9 top-0.5 text-[10px] font-mono text-slate-400 opacity-0 group-hover:opacity-100 select-none">
          ¶{p.pid}
        </span>
      )}
      {p.list && <span className="absolute left-1">•</span>}
      {p.items.map((item, i) => (
        <Item key={i} item={item} model={model} onSelect={onSelect}
          selected={selection?.kind === 'image' && 'index' in selection && 'image' in item && selection.index === item.image} />
      ))}
    </div>
  );
}

function Table({ table, model, selection, onSelect }: {
  table: DocxTable; model: DocxPreviewModel; selection: Selection | null; onSelect: (s: Selection | null) => void;
}) {
  return (
    <table className="w-full border-collapse my-2 text-left">
      <tbody>
        {table.rows.map((row, r) => (
          <tr key={r}>
            {row.map((cell, c) => (
              <td key={c} className="border border-slate-300 align-top px-2 py-1" style={{ background: cell.fill ?? undefined }}>
                {cell.paragraphs.map((p, i) => (
                  <Paragraph key={i} p={p} model={model} selection={selection} onSelect={onSelect} />
                ))}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export const DocxPreview: React.FC<DocxPreviewProps> = ({ model, zoom, selection, onSelect }) => {
  const { page } = model;
  const blocks = (list: (DocxParagraph | DocxTable)[]) =>
    list.map((block, i) =>
      block.kind === 'table'
        ? <Table key={i} table={block} model={model} selection={selection} onSelect={onSelect} />
        : <Paragraph key={i} p={block} model={model} selection={selection} onSelect={onSelect} />,
    );
  return (
    <div className="flex justify-center py-6 px-4 min-w-fit" onClick={() => onSelect(null)}>
      <div
        className="bg-white shadow-xl shadow-black/30 text-black"
        style={{
          zoom,
          width: page.width / TWIPS_PER_PX,
          minHeight: page.height / TWIPS_PER_PX,
          padding: `${page.margin_top / TWIPS_PER_PX}px ${page.margin_right / TWIPS_PER_PX}px ${page.margin_top / TWIPS_PER_PX}px ${page.margin_left / TWIPS_PER_PX}px`,
          fontFamily: 'Calibri, Arial, sans-serif',
        }}
      >
        {model.header.length > 0 && (
          <div className="border-b border-dashed border-slate-200 mb-4 pb-2" aria-label="Page header">{blocks(model.header)}</div>
        )}
        {blocks(model.blocks)}
        {model.footer.length > 0 && (
          <div className="border-t border-dashed border-slate-200 mt-6 pt-2" aria-label="Page footer">{blocks(model.footer)}</div>
        )}
      </div>
    </div>
  );
};
