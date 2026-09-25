import React, { useEffect, useRef, useState } from 'react';
import { FileText, ImageIcon, MousePointerClick, Paperclip, Presentation, RefreshCw, Send, Trash2, X } from 'lucide-react';

import { WorkspaceApi } from '../../workspace/useWorkspace';
import { ChatMessageBubble } from './ChatMessageBubble';

const SUGGESTIONS = {
  docx: [
    'Change the document title font to Arial and make it bold.',
    'Change the title color to blue.',
    'Remove the paragraph about enterprise architecture.',
    'Add this paragraph after the executive summary: Our platform helps enterprises automate document workflows.',
    'Make the company logo 80% of its current size.',
  ],
  pptx: [
    'Change the title on slide 1 to Arial, 32 points.',
    'Remove the third bullet from slide 2.',
    'Add a bullet to slide 3: Live preview of every change',
    'Resize the logo on slide 1 to 80%.',
    'Move the logo slightly to the right.',
  ],
};

const STATUS_TEXT = {
  sending: 'Parsing your instruction and editing the file…',
  uploading: 'Uploading…',
  opening: 'Opening the document…',
  loading: 'Loading workspace…',
  idle: '',
};

export const ChatPanel: React.FC<{ ws: WorkspaceApi }> = ({ ws }) => {
  const [draft, setDraft] = useState('');
  const listRef = useRef<HTMLDivElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const active = ws.state?.active ?? null;
  const busy = ws.status !== 'idle';

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' });
  }, [ws.messages.length, busy]);

  const submit = (text: string) => {
    if (!text.trim() || busy || !active) return;
    ws.send(text);
    setDraft('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit(draft);
    }
  };

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = ''; // picking the same file again should still fire onChange
    if (file) ws.upload(file);
  };

  const TypeIcon = active?.type === 'pptx' ? Presentation : FileText;

  return (
    <div className="flex flex-col h-full min-h-0 bg-slate-900">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-slate-800">
        <div className="min-w-0 flex-1">
          <h2 className="text-sm font-semibold text-white">AI Document Editor</h2>
          {active ? (
            <p className="text-xs text-slate-400 flex items-center gap-1.5 truncate">
              <TypeIcon className="w-3.5 h-3.5 flex-shrink-0" aria-hidden />
              <span className="truncate">{active.name}</span>
              <span className="font-mono text-amber-300">{active.version}</span>
            </p>
          ) : (
            <p className="text-xs text-slate-400">No document open</p>
          )}
        </div>
        <span
          className={`text-[10px] px-2 py-0.5 rounded-full border ${ws.state?.parser === 'gemini' ? 'text-violet-300 border-violet-500/40 bg-violet-500/10' : 'text-slate-300 border-slate-600'}`}
          title="Component that converts your message into a structured edit command"
        >
          {ws.state?.parser === 'gemini' ? 'Gemini + rules fallback' : 'Built-in parser'}
        </span>
        <button
          onClick={ws.clear}
          disabled={busy || !ws.messages.length}
          className="p-1.5 rounded-md text-slate-400 hover:text-white hover:bg-slate-800 disabled:opacity-40 cursor-pointer"
          aria-label="Clear conversation"
          title="Clear conversation"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>

      {/* Conversation */}
      <div ref={listRef} className="flex-1 min-h-0 overflow-y-auto px-4 py-4 space-y-4" aria-live="polite">
        {ws.messages.length === 0 && (
          <div className="text-center text-sm text-slate-400 py-10 space-y-2">
            <p className="text-slate-200 font-medium">Edit documents by chatting</p>
            <p>Open a Word or PowerPoint file on the right, then describe the change you want.</p>
          </div>
        )}
        {ws.messages.map((m) => (
          <ChatMessageBubble key={m.id} message={m} onPickOption={(n) => submit(String(n))} disabled={busy} />
        ))}
        {busy && ws.status !== 'loading' && (
          <div className="flex items-center gap-2 text-xs text-slate-400 pl-9">
            <RefreshCw className="w-3.5 h-3.5 animate-spin" aria-hidden />
            {STATUS_TEXT[ws.status]}
          </div>
        )}
      </div>

      {/* Suggestions */}
      {active && (
        <div className="px-4 pb-2 flex gap-1.5 overflow-x-auto ws-no-scrollbar">
          {SUGGESTIONS[active.type].map((s) => (
            <button
              key={s}
              onClick={() => setDraft(s)}
              disabled={busy}
              className="text-[11px] whitespace-nowrap bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 px-2.5 py-1 rounded-full cursor-pointer disabled:opacity-50"
            >
              {s.length > 48 ? `${s.slice(0, 46)}…` : s}
            </button>
          ))}
        </div>
      )}

      {/* Context chips */}
      {(ws.selection || ws.state?.pending_image) && (
        <div className="px-4 pb-2 flex flex-wrap gap-1.5">
          {ws.selection && (
            <span className="inline-flex items-center gap-1 text-[11px] bg-blue-500/15 text-blue-200 border border-blue-500/40 px-2 py-0.5 rounded-full">
              <MousePointerClick className="w-3 h-3" aria-hidden />
              Selected: {ws.selection.label} — say “this”
              <button onClick={() => ws.setSelection(null)} aria-label="Clear selection" className="cursor-pointer">
                <X className="w-3 h-3" />
              </button>
            </span>
          )}
          {ws.state?.pending_image && (
            <span className="inline-flex items-center gap-1 text-[11px] bg-emerald-500/15 text-emerald-200 border border-emerald-500/40 px-2 py-0.5 rounded-full">
              <ImageIcon className="w-3 h-3" aria-hidden />
              {ws.state.pending_image.name} ready to use as the new logo
            </span>
          )}
        </div>
      )}

      {/* Composer */}
      <div className="p-3 border-t border-slate-800">
        <div className="flex items-end gap-2 bg-slate-950 border border-slate-700 rounded-xl p-2 focus-within:border-blue-500">
          <input
            ref={fileRef}
            type="file"
            className="hidden"
            accept=".docx,.pptx,.png,.jpg,.jpeg,.gif"
            onChange={handleFile}
          />
          <button
            onClick={() => fileRef.current?.click()}
            disabled={busy}
            className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 disabled:opacity-40 cursor-pointer"
            aria-label="Upload a document or logo image"
            title="Upload a .docx / .pptx to edit, or an image to use as the new logo"
          >
            <Paperclip className="w-4 h-4" />
          </button>
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={Math.min(5, Math.max(1, draft.split('\n').length))}
            placeholder={active ? 'Describe a change… (Enter to send, Shift+Enter for a new line)' : 'Open a document to start editing'}
            disabled={!active}
            aria-label="Edit instruction"
            className="flex-1 resize-none bg-transparent text-sm text-slate-100 placeholder-slate-500 focus:outline-none py-1.5 max-h-40"
          />
          <button
            onClick={() => submit(draft)}
            disabled={busy || !draft.trim() || !active}
            className="p-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white disabled:opacity-40 cursor-pointer"
            aria-label="Send"
          >
            {ws.status === 'sending' ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          </button>
        </div>
      </div>
    </div>
  );
};
