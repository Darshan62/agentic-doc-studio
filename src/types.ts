export interface AgentStep {
  step_num: number;
  agent: string;
  action: string;
  detail: string;
  status: 'pending' | 'running' | 'completed' | 'error';
  artifacts?: string[];
}

export interface Citation {
  id: string;
  source_type: 'web' | 'rag';
  title: string;
  reference: string;
  snippet: string;
  confidence: number;
  timestamp?: number;
}

export interface VersionRecord {
  version: string;
  timestamp: number;
  author: string;
  instruction: string;
  diff_summary: string[];
  doc_path?: string;
  ppt_path?: string;
  changes_count: number;
}

export interface ValidationScorecard {
  artifact: string;
  file_path: string;
  status: string;
  quality_score: number;
  checks: Record<string, boolean | number>;
}

export interface SystemStatus {
  status: string;
  kb_chunks_indexed: number;
  kb_documents: string[];
  versions_count: number;
  versions: VersionRecord[];
  gemini_key_set: boolean;
}

// ----- Content written by Gemini (same shape as agents/content_writer.py) -----
export interface DocSection {
  heading: string;
  paragraphs: string[];
  bullets: string[];
  table: { headers: string[]; rows: string[][] } | null;
}

export interface DeckSlide {
  layout: 'bullets' | 'two_column' | 'three_pillar' | 'metrics' | 'table';
  title: string;
  summary?: string;
  subtitle?: string;
  points?: string[];
  left_title?: string;
  left_points?: string[];
  right_title?: string;
  right_points?: string[];
  pillars?: { title: string; desc: string; metric: string }[];
  metrics?: { value: string; label: string; desc: string }[];
  headers?: string[];
  rows?: string[][];
}

export interface GeneratedContent {
  document: { title: string; subtitle: string; executive_summary: string; sections: DocSection[] };
  deck: { title: string; subtitle: string; slides: DeckSlide[] };
}

export interface OrchestrationResult {
  status: string;
  prompt: string;
  generated_docx: string;
  generated_pptx: string;
  content: GeneratedContent;
  validation: {
    docx: ValidationScorecard;
    pptx: ValidationScorecard;
    traceability: { status: string; total_sources: number; sources_cited_in_text: number; uncited_sources: string[] };
  };
  citations_count: number;
  citations: Citation[];
  execution_steps: AgentStep[];
}

export interface EditResult {
  status: string;
  instruction: string;
  version: string;
  diff_summary: string[];
  content: GeneratedContent;
  artifacts: { docx: string; pptx: string };
}

export interface UploadResult {
  status: string;
  filename: string;
  path: string;
  ingest: { chunks_indexed: number; words: number; warning?: string } | null;
}
