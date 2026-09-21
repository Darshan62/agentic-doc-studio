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
  checks: Record<string, any>;
}

export interface SystemStatus {
  status: string;
  kb_chunks_indexed: number;
  kb_documents: string[];
  versions_count: number;
  versions: VersionRecord[];
  sample_files: {
    docx_template: string;
    pptx_template: string;
    ocr_brief: string;
  };
  active_artifacts: {
    docx: string | null;
    pptx: string | null;
    zip: string | null;
  };
}

export interface OrchestrationResult {
  status: string;
  prompt: string;
  generated_docx: string;
  generated_pptx: string;
  validation: {
    docx: ValidationScorecard;
    pptx: ValidationScorecard;
    traceability: Record<string, any>;
  };
  citations_count: number;
  citations: Citation[];
  execution_steps: AgentStep[];
}
