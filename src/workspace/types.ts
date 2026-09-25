// Shapes returned by the Python workspace agent (agents/workspace_agent.py and core/*_preview.py)

export type DocType = 'docx' | 'pptx';

export interface TextRun {
  text: string;
  font: string | null;
  size: number;
  bold: boolean;
  italic: boolean;
  underline: boolean;
  color: string | null;
}

export interface DocxImageItem {
  image: number;
  media: string | null;
  name: string;
  width: number;
  height: number;
  changed: boolean;
}

export type DocxItem = TextRun | DocxImageItem;

export interface DocxParagraph {
  kind: 'p';
  pid: number | null;
  role: 'title' | 'subtitle' | 'heading' | 'body';
  align: string | null;
  level: number | null;
  list: boolean;
  changed: boolean;
  items: DocxItem[];
  size: number;
}

export interface DocxTable {
  kind: 'table';
  rows: { fill: string | null; paragraphs: DocxParagraph[] }[][];
}

export interface DocxPreviewModel {
  type: 'docx';
  page: { width: number; height: number; margin_left: number; margin_right: number; margin_top: number };
  header: DocxParagraph[];
  footer: DocxParagraph[];
  blocks: (DocxParagraph | DocxTable)[];
  media: Record<string, string>;
  images: { index: number; name: string; location: string; label: string; width_in: string; height_in: string }[];
}

export interface SlideParagraph {
  align: string;
  level: number;
  bullet: string | null;
  runs: TextRun[];
  size: number;
  space_before: number;
}

export interface SlideShape {
  id: string;
  name: string;
  kind: 'text' | 'picture' | 'shape';
  x: number;
  y: number;
  cx: number;
  cy: number;
  changed: boolean;
  is_title: boolean;
  media?: string | null;
  is_logo?: boolean;
  fill?: string | null;
  geometry?: string;
  line?: string | null;
  line_width?: number;
  paragraphs?: SlideParagraph[];
  anchor?: string;
  inset?: number[];
}

export interface SlideModel {
  index: number;
  background: string;
  title: string;
  changed: boolean;
  shapes: SlideShape[];
}

export interface PptxPreviewModel {
  type: 'pptx';
  width: number;
  height: number;
  slides: SlideModel[];
  media: Record<string, string>;
}

export type PreviewModel = DocxPreviewModel | PptxPreviewModel;

export interface ChangedRefs {
  paragraphs?: number[];
  images?: number[];
  slides?: number[];
  shapes?: string[];
}

export type EditCommand = Record<string, unknown>;

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  ts: number;
  status?: 'done' | 'error' | 'clarify' | 'info';
  parser?: string;
  note?: string | null;
  commands?: EditCommand[];
  version?: string;
  options?: string[];
}

export interface ActiveArtifact {
  name: string;
  type: DocType;
  version: string;
  version_index: number;
  can_undo: boolean;
  can_redo: boolean;
}

export interface VersionEntry {
  version: string;
  instruction: string;
  timestamp: number;
  changes: string[];
}

export interface WorkspaceState {
  messages: ChatMessage[];
  active: ActiveArtifact | null;
  preview: PreviewModel | null;
  versions: VersionEntry[];
  pending_image: { name: string; width: number; height: number } | null;
  parser: 'gemini' | 'rules';
}

export interface ArtifactFile {
  path: string;
  name: string;
  group: string;
  type: DocType;
}

export interface WorkspaceResponse {
  status: 'ok' | 'done' | 'clarify' | 'error';
  state?: WorkspaceState;
  error?: string;
  changed?: ChangedRefs;
  artifacts?: ArtifactFile[];
}

// What the user clicked in the preview; "this"/"selected" in a message refers to it
export type Selection =
  | { kind: 'paragraph'; pid: number; label: string }
  | { kind: 'image'; index: number; label: string }
  | { kind: 'shape' | 'image'; slide: number; shape_id: string; label: string };
