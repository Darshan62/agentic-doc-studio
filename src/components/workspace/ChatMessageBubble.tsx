import React from 'react';
import { AlertTriangle, Bot, CheckCircle2, HelpCircle, Info, User } from 'lucide-react';

import { ChatMessage, EditCommand } from '../../workspace/types';

interface ChatMessageBubbleProps {
  message: ChatMessage;
  onPickOption: (index: number) => void;
  disabled: boolean;
}

const STATUS_STYLE = {
  done: { icon: CheckCircle2, color: 'text-emerald-400', border: 'border-emerald-500/30' },
  error: { icon: AlertTriangle, color: 'text-red-400', border: 'border-red-500/40' },
  clarify: { icon: HelpCircle, color: 'text-amber-400', border: 'border-amber-500/40' },
  info: { icon: Info, color: 'text-sky-400', border: 'border-slate-700' },
} as const;

function describeTarget(target: unknown): string {
  if (!target || typeof target !== 'object') return '';
  const t = target as Record<string, unknown>;
  const parts = t.type === 'slide' ? [] : [String(t.type ?? '')];
  if (t.index !== undefined) parts.push(`#${t.index}`);
  if (t.text) parts.push(`“${String(t.text).slice(0, 30)}”`);
  if (t.slide) parts.push(`slide ${t.slide}`);
  return parts.join(' ');
}

function CommandChips({ commands }: { commands: EditCommand[] }) {
  return (
    <div className="flex flex-wrap gap-1.5 mt-2">
      {commands.map((cmd, i) => (
        <span key={i} className="text-[10px] font-mono bg-slate-950/70 border border-slate-700 text-cyan-300 px-1.5 py-0.5 rounded">
          {String(cmd.action)}
          {cmd.target ? <span className="text-slate-400"> → {describeTarget(cmd.target)}</span> : null}
        </span>
      ))}
    </div>
  );
}

export const ChatMessageBubble: React.FC<ChatMessageBubbleProps> = ({ message, onPickOption, disabled }) => {
  if (message.role === 'user') {
    return (
      <div className="flex justify-end gap-2">
        <div className="max-w-[85%] bg-blue-600 text-white text-sm rounded-2xl rounded-tr-sm px-3.5 py-2 whitespace-pre-wrap break-words">
          {message.text}
        </div>
        <div className="w-7 h-7 rounded-full bg-slate-700 flex items-center justify-center flex-shrink-0">
          <User className="w-4 h-4 text-slate-300" aria-hidden />
        </div>
      </div>
    );
  }

  const style = STATUS_STYLE[message.status ?? 'info'];
  const StatusIcon = style.icon;
  return (
    <div className="flex gap-2">
      <div className="w-7 h-7 rounded-full bg-gradient-to-br from-blue-600 to-indigo-700 flex items-center justify-center flex-shrink-0">
        <Bot className="w-4 h-4 text-white" aria-hidden />
      </div>
      <div className={`max-w-[88%] bg-slate-800/80 border ${style.border} rounded-2xl rounded-tl-sm px-3.5 py-2.5 text-sm text-slate-100`}>
        <div className="flex gap-2 items-start">
          <StatusIcon className={`w-4 h-4 mt-0.5 flex-shrink-0 ${style.color}`} aria-label={message.status ?? 'info'} />
          <p className="whitespace-pre-wrap break-words leading-relaxed">{message.text}</p>
        </div>

        {message.options && message.options.length > 0 && (
          <ol className="mt-2 space-y-1">
            {message.options.map((label, i) => (
              <li key={i}>
                <button
                  onClick={() => onPickOption(i + 1)}
                  disabled={disabled}
                  className="w-full text-left text-xs bg-slate-900/80 hover:bg-slate-700 border border-slate-700 rounded-lg px-2.5 py-1.5 cursor-pointer disabled:opacity-50"
                >
                  <span className="font-mono text-amber-300 mr-1.5">{i + 1}.</span>
                  {label}
                </button>
              </li>
            ))}
          </ol>
        )}

        {message.commands && message.commands.length > 0 && message.status === 'done' && (
          <CommandChips commands={message.commands} />
        )}

        {(message.version || message.parser || (message.commands && message.commands.length > 0)) && (
          <div className="mt-2 flex flex-wrap items-center gap-2 text-[10px] text-slate-400">
            {message.version && (
              <span className="font-mono bg-amber-500/15 text-amber-300 border border-amber-500/30 px-1.5 py-0.5 rounded">
                {message.version}
              </span>
            )}
            {message.parser && message.parser !== 'choice' && (
              <span title="Which component turned the request into an edit command">
                parsed by {message.parser === 'gemini' ? 'Gemini' : 'built-in rules'}
              </span>
            )}
            {message.commands && message.commands.length > 0 && (
              <details className="w-full">
                <summary className="cursor-pointer hover:text-slate-200">Structured command (JSON)</summary>
                <pre className="mt-1 max-h-48 overflow-auto bg-slate-950 border border-slate-800 rounded p-2 text-[10px] text-cyan-200">
                  {JSON.stringify(message.commands, null, 2)}
                </pre>
              </details>
            )}
          </div>
        )}
        {message.note && <p className="mt-1.5 text-[10px] italic text-slate-500">{message.note}</p>}
      </div>
    </div>
  );
};
