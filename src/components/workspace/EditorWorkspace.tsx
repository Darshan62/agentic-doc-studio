import React from 'react';
import { AlertCircle, X } from 'lucide-react';

import { useWorkspace } from '../../workspace/useWorkspace';
import { ChatPanel } from './ChatPanel';
import { PreviewPanel } from './PreviewPanel';

// Split-screen editor: chat on the left (~38%), live document preview on the right (~62%).
// Below the lg breakpoint the two panels stack vertically.
export const EditorWorkspace: React.FC = () => {
  const ws = useWorkspace();
  return (
    <div className="flex flex-col flex-1 min-h-0">
      {ws.error && (
        <div role="alert" className="flex items-start gap-2 bg-red-950/70 border-b border-red-800 text-red-200 text-sm px-4 py-2">
          <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" aria-hidden />
          <span className="flex-1">{ws.error}</span>
          <button onClick={ws.dismissError} aria-label="Dismiss error" className="cursor-pointer">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}
      <div className="flex flex-col lg:flex-row flex-1 min-h-0">
        <section className="h-[70vh] lg:h-auto lg:w-[38%] lg:max-w-[560px] flex-shrink-0 border-b lg:border-b-0 lg:border-r border-slate-800 min-h-0">
          <ChatPanel ws={ws} />
        </section>
        <section className="h-[85vh] lg:h-auto flex-1 min-w-0 min-h-0">
          <PreviewPanel ws={ws} />
        </section>
      </div>
    </div>
  );
};
