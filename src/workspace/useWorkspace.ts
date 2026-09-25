import { useCallback, useEffect, useRef, useState } from 'react';

import { errorMessage, postJson } from '../api';
import { ArtifactFile, ChangedRefs, ChatMessage, Selection, WorkspaceResponse, WorkspaceState } from './types';

const MAX_UPLOAD_MB = 25;

export type WorkspaceStatus = 'loading' | 'idle' | 'sending' | 'uploading' | 'opening';

async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(url);
  const data = await res.json().catch(() => ({ error: `Server returned ${res.status}` }));
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
  return data as T;
}

function readAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = () => reject(new Error('Could not read the file'));
    reader.readAsDataURL(file);
  });
}

// The selection is sent without its UI label
function selectionPayload(selection: Selection | null) {
  if (!selection) return null;
  const { label: _label, ...rest } = selection;
  return rest;
}

export function useWorkspace() {
  const [state, setState] = useState<WorkspaceState | null>(null);
  const [artifacts, setArtifacts] = useState<ArtifactFile[]>([]);
  const [status, setStatus] = useState<WorkspaceStatus>('loading');
  const [error, setError] = useState<string | null>(null);
  const [selection, setSelection] = useState<Selection | null>(null);
  const [currentSlide, setCurrentSlide] = useState(1);
  const [changed, setChanged] = useState<ChangedRefs | null>(null);
  const [pendingText, setPendingText] = useState<string | null>(null);
  const isMounted = useRef(true);

  const slideCount = state?.preview?.type === 'pptx' ? state.preview.slides.length : 0;

  const apply = useCallback((res: WorkspaceResponse) => {
    if (!isMounted.current) return;
    if (res.state) setState(res.state);
    setChanged(res.changed ?? null);
    if (res.state?.preview?.type === 'pptx') {
      const total = res.state.preview.slides.length;
      const target = res.changed?.slides?.[0];
      setCurrentSlide((prev) => Math.min(Math.max(target ?? prev, 1), Math.max(total, 1)));
    }
  }, []);

  const run = useCallback(
    async (next: WorkspaceStatus, action: () => Promise<WorkspaceResponse>) => {
      setStatus(next);
      setError(null);
      try {
        apply(await action());
      } catch (err) {
        if (isMounted.current) setError(errorMessage(err));
      } finally {
        if (isMounted.current) {
          setStatus('idle');
          setPendingText(null);
        }
      }
    },
    [apply],
  );

  const refreshArtifacts = useCallback(async () => {
    try {
      const res = await getJson<WorkspaceResponse>('/api/workspace/artifacts');
      if (isMounted.current) setArtifacts(res.artifacts ?? []);
    } catch (err) {
      if (isMounted.current) setError(errorMessage(err));
    }
  }, []);

  useEffect(() => {
    isMounted.current = true;
    run('loading', () => getJson<WorkspaceResponse>('/api/workspace/state'));
    refreshArtifacts();
    return () => {
      isMounted.current = false;
    };
  }, [run, refreshArtifacts]);

  const open = useCallback(
    (path: string) => {
      setSelection(null);
      setCurrentSlide(1);
      return run('opening', () => postJson<WorkspaceResponse>('/api/workspace/open', { path }));
    },
    [run],
  );

  const upload = useCallback(
    async (file: File) => {
      if (file.size > MAX_UPLOAD_MB * 1024 * 1024) {
        setError(`${file.name} is too large (max ${MAX_UPLOAD_MB} MB).`);
        return;
      }
      const isDocument = /\.(docx|pptx)$/i.test(file.name);
      if (isDocument) {
        setSelection(null);
        setCurrentSlide(1);
      }
      await run('uploading', async () => {
        const base64Content = await readAsDataUrl(file);
        return postJson<WorkspaceResponse>('/api/workspace/upload', { filename: file.name, base64Content });
      });
      if (isDocument) refreshArtifacts();
    },
    [run, refreshArtifacts],
  );

  const send = useCallback(
    (message: string) => {
      const text = message.trim();
      if (!text || status !== 'idle') return;
      setPendingText(text);
      return run('sending', async () => {
        const res = await postJson<WorkspaceResponse>('/api/workspace/chat', {
          message: text,
          selection: selectionPayload(selection),
          current_slide: currentSlide,
        });
        // Positions shift after an edit, so an old selection could point at the wrong thing
        if (res.status === 'done') setSelection(null);
        return res;
      });
    },
    [run, status, selection, currentSlide],
  );

  const simple = useCallback(
    (op: 'undo' | 'redo' | 'clear') => run('sending', () => postJson<WorkspaceResponse>(`/api/workspace/${op}`, {})),
    [run],
  );

  const restore = useCallback(
    (version: string) => run('sending', () => postJson<WorkspaceResponse>('/api/workspace/restore', { version })),
    [run],
  );

  // The user's message is shown right away while the agents work
  const messages: ChatMessage[] = [...(state?.messages ?? [])];
  if (pendingText) {
    messages.push({ id: 'pending', role: 'user', text: pendingText, ts: Date.now() / 1000 });
  }

  return {
    state,
    messages,
    artifacts,
    status,
    error,
    dismissError: () => setError(null),
    selection,
    setSelection,
    currentSlide,
    setCurrentSlide: (n: number) => setCurrentSlide(Math.min(Math.max(n, 1), Math.max(slideCount, 1))),
    changed,
    open,
    upload,
    send,
    undo: () => simple('undo'),
    redo: () => simple('redo'),
    clear: () => simple('clear'),
    restore,
  };
}

export type WorkspaceApi = ReturnType<typeof useWorkspace>;
