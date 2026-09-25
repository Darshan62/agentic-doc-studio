# Enterprise Multi-Agent AI System: Document & PPT Generation POC

An enterprise-grade multi-agent AI chatbot platform designed to understand complex user requests, analyze uploaded documents and PowerPoint templates, conduct web research, retrieve proprietary knowledge through Enterprise Vector RAG, and autonomously generate **fully editable Microsoft Word documents (.docx) and 12-slide PowerPoint presentations (.pptx)**.

The platform features:

- A Supervisor/Orchestrator coordinating 9 specialized sub-agents.
- Multi-format document ingestion, including DOCX, PPTX, PDF, and scanned images.
- OCR and vision-based document analysis.
- Template-aware document and presentation generation.
- Enterprise knowledge retrieval using vector search and RAG.
- Conversational in-place editing and bidirectional DOCX/PPTX conversion.
- Citation provenance, validation, and version management.

---

## ✍️ AI Editor Workspace (chat-driven DOCX/PPTX editing)

The default **AI Editor Workspace** tab is a split screen: chat on the left, a live preview of the open
`.docx` / `.pptx` on the right. Plain-English requests become validated JSON edit commands that a
deterministic OpenXML editor applies to the real file. The model never writes code or XML.

```
message → Edit Intent Parser (Gemini, JSON only; built-in rule parser as fallback)
        → core/edit_schema.py validate_command (whitelisted actions / targets / values)
        → core/docx_editor.py or core/pptx_editor.py (targeted in-place XML edits)
        → saved working copy + version snapshot (v1.0, v1.1, …) → preview JSON → chat reply
```

| Word (.docx) | PowerPoint (.pptx) |
|---|---|
| `update_style` (font, size, bold, italic, underline, colour, alignment) | `update_style` |
| `update_text`, `replace_text`, `delete_text`, `insert_text` | `update_text`, `replace_text`, `delete_text` (text or bullet) |
| `delete_paragraph`, `insert_paragraph` (after/before a heading or paragraph, start, end) | `add_text` (new bullet), `delete_slide` |
| `replace_image`, `resize_image` (the logo) | `replace_image`, `resize_image`, `move_image` |

- Ambiguous requests get a clarifying question (with clickable options when several paragraphs/images match).
- Click a paragraph, text box or the logo in the preview, then say “this” (“Remove this paragraph”).
- Every successful edit is a new version. Undo/redo and the version menu restore earlier versions.
- The original file is never modified: the workspace edits a copy in `output/workspace/`.
- Demo files: `python -m templates_and_samples.create_demo_files` rebuilds `templates_and_samples/demo/`.
- `EDIT_PARSER=auto|gemini|rules` (default `auto`: Gemini first, rule parser on any Gemini failure).
- Run: `npm install`, `pip install -r requirements.txt`, `npm run dev`, then open http://127.0.0.1:3000.
- Tests: `python -m unittest tests.test_multi_agent_system tests.test_edit_engine tests.test_edit_operations tests.test_editor_workspace`.

---

## 🏛️ System Architecture

```text
                    ┌─────────────────────────────┐
                    │       User Prompt/Input     │
                    └──────────────┬──────────────┘
                                   ▼
                    ┌─────────────────────────────┐
                    │  Supervisor / Orchestrator  │
                    └──────────────┬──────────────┘
                                   │
           ┌───────────────────────┼───────────────────────┐
           ▼                       ▼                       ▼
 ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
 │ Document Analyzer│   │   PPT Analyzer   │   │  Web Researcher  │
 │   DOCX/PDF/OCR   │   │ PPTX Templates   │   │  Real-Time Search│
 └─────────┬────────┘   └─────────┬────────┘   └─────────┬────────┘
           │                      │                      │
           └──────────────────────┼──────────────────────┘
                                  ▼
                       ┌────────────────────┐
                       │   Enterprise RAG   │
                       │  Vector DB / KB     │
                       └─────────┬──────────┘
                                 ▼
                    ┌─────────────────────────────┐
                    │      Generation Agents      │
                    ├──────────────┬──────────────┤
                    │ Doc Generator│ PPT Generator│
                    └───────┬──────┴──────┬───────┘
                            │             │
                            └──────┬──────┘
                                   ▼
                    ┌─────────────────────────────┐
                    │       Validation Agent      │
                    │   Style, QA, Grounding      │
                    └──────────────┬──────────────┘
                                   ▼
                    ┌─────────────────────────────┐
                    │ Editable DOCX & 12-Slide PPTX│
                    └──────────────┬──────────────┘
                                   ▼
                    ┌─────────────────────────────┐
                    │ Conversational Editor &     │
                    │ Conversion Engine           │
                    └─────────────────────────────┘
```

---

## 🤖 Specialized Multi-Agent Roles

| Agent | Architecture Role | Responsibility |
|---|---|---|
| Supervisor / Orchestrator | Central Controller | Decomposes tasks into execution graphs, tracks inter-agent state, enforces validation gates, and records execution traces through `AgentStepLog`. |
| Document Analysis Agent | File Inspector | Analyzes DOCX, PDF, and scanned documents. Extracts typography, color palettes, margins, heading hierarchies, and tone of voice. |
| PPT Analysis Agent | Presentation Inspector | Analyzes PowerPoint templates, slide masters, 16:9 geometries, theme palettes, layouts, and content patterns. |
| Web Research Agent | Real-Time Intelligence | Formulates search queries, gathers industry information, and produces source citations. |
| Enterprise RAG Agent | Knowledge Grounding | Retrieves proprietary policies, SLAs, and technical directives from the enterprise vector database. |
| Document Generation Agent | Word Synthesis | Generates professional Word proposals with styled headings, executive summaries, tables, and citations. |
| PPT Generation Agent | Presentation Synthesis | Generates 12-slide widescreen presentations with structured layouts, dashboards, diagrams, roadmaps, and citations. |
| Validation Agent | QA & Compliance | Validates OpenXML integrity, slide count, template styling, and citation coverage. |
| Conversational Editing Agent | In-Place Refinement | Applies natural-language editing instructions while preserving the existing design system. |
| Conversion Agent | Format Translation | Converts Word proposals to PowerPoint decks and PowerPoint decks to Word reports. |

---

## 📂 Core Engine Capabilities

### 1. Native OpenXML Engine

The platform uses a Python-based OpenXML builder and parser:

- `core/ooxml_docx.py`
- `core/ooxml_pptx.py`

It generates editable DOCX and PPTX files compatible with Microsoft Office 365, LibreOffice, and Google Docs without requiring desktop Office binaries.

### 2. Multi-Format Ingestion & Vision OCR

Supported document formats:

| Format | Processing |
|---|---|
| DOCX | Parses XML packages, styles, headings, tables, and formatting. |
| PPTX | Extracts slide masters, layouts, theme colors, and presentation structure. |
| PDF | Uses a custom parser to extract text operators and document structure. |
| PNG, JPG, TIFF | Uses the vision/OCR processing module to inspect layout zones and extract textual content. |

Core modules:

- `core/pdf_parser.py`
- `core/ocr_vision.py`

### 3. Enterprise Vector RAG & Local Embedding Engine

The retrieval system includes:

- **Pinecone-compatible architecture:** Modular adapter for enterprise cloud Pinecone instances.
- **Dense vector search:** NumPy-based semantic search using hashed n-gram tokenization.
- **Similarity scoring:** L2 normalization and cosine similarity.
- **Sliding-window chunking:** 400-character chunks with 80-character overlap.
- **Persistent storage:** SQLite-backed knowledge storage.

Core module: `core/vector_store.py`

### 4. Source Traceability & Versioning

The system provides:

- Citation tags such as `[Web-1]` and `[RAG-1]`.
- Reference URLs, supporting evidence, confidence scores, and timestamps.
- Version snapshots such as `v1.0`, `v1.1`, and `v2.0`.
- Unified diff calculation and changelog audit logging.

Core modules:

- `core/version_manager.py`
- `core/citation_tracker.py`

---

## 🚀 Example Workflow & Verification

The end-to-end demonstration is implemented through `demo_workflow.py` and `tests/test_all.py`.

### Step 1: Template Analysis

The Document Analyzer and PPT Analyzer inspect uploaded templates.

**Sample DOCX analysis:**

- Primary font: Georgia
- Palette: Navy `#1B365D`, Cyan `#00A3E0`
- Tone: Executive, strategic, analytical, and formal
- Tone score: 0.95

**Sample PPTX analysis:**

- Master: 16:9 widescreen
- Dimensions: `12192000 × 6858000 EMU`
- Font: Arial
- Palette: Navy `#0F2D59`, Blue `#2563EB`, Emerald `#10B981`

### Step 2: User Request Processing

Example prompt:

> Research the latest Generative AI trends and create a proposal and 12-slide presentation using the same tone and style as the uploaded files.

The Supervisor decomposes the request into a multi-stage execution graph.

Generated artifacts:

- `output/Company_Proposal_Generated.docx`
- `output/Company_Presentation_Generated.pptx`

### Step 3: Validation

The Validation Agent checks:

- OpenXML integrity
- Presentation slide count
- Citation coverage
- Template style adherence

**Reported demonstration results:**

- Quality score: 100.0%
- OpenXML integrity: PASS
- Slide count: 12 — PASS
- Citations: 7 — PASS

### Step 4: Citation Traceability

Example sources recorded in the demonstration:

- `[Web-1]` Gartner Top Strategic Technology Trends 2025
- `[Web-2]` McKinsey Global Institute: Economic Potential of Generative AI in 2025
- `[Web-3]` Stanford AI Index 2024
- `[Web-4]` MIT Technology Review: Domain-Specific Small Language Models
- `[Web-5]` IDC Enterprise AI Governance and EU AI Act Implementation Framework
- `[RAG-1]` Acme Enterprise AI Strategy 2025

### Step 5: Conversational Refinements

| User Instruction | Demonstrated Action |
|---|---|
| Add an executive summary. | Adds an executive summary callout to the DOCX and a summary slide to the PPTX. |
| Make the presentation more concise. | Condenses slide bullets by 40%. |
| Add a competitive analysis section. | Adds a five-column competitive matrix to the DOCX and PPTX. |
| Update the report using the latest web information. | Runs a fresh web query, updates information, and advances the version to v2.0. |

### Step 6: Bidirectional Conversion

The conversion engine supports:

- DOCX proposal → 16:9 PowerPoint presentation
- PPTX presentation → narrative Word report

Example outputs:

- `output/Converted_From_Proposal.pptx`
- `output/Converted_From_Presentation.docx`

---

## 📁 Repository Structure

```text
multi_agent_doc_ppt/
│
├── app.py
├── demo_workflow.py
├── requirements.txt
├── README.md
├── knowledge_store.db
│
├── agents/
│   ├── supervisor.py
│   ├── document_analyzer.py
│   ├── ppt_analyzer.py
│   ├── web_researcher.py
│   ├── rag_agent.py
│   ├── doc_generator.py
│   ├── ppt_generator.py
│   ├── validator.py
│   ├── conversational_editor.py
│   └── converter.py
│
├── core/
│   ├── models.py
│   ├── ooxml_docx.py
│   ├── ooxml_pptx.py
│   ├── pdf_parser.py
│   ├── ocr_vision.py
│   ├── vector_store.py
│   ├── version_manager.py
│   └── citation_tracker.py
│
├── api/
│   ├── server.py
│   └── web_ui.py
│
├── templates_and_samples/
│   ├── Company_Proposal.docx
│   ├── Company_Template.pptx
│   ├── Scanned_Architecture_Brief.png
│   ├── create_samples.py
│   └── knowledge_base/
│       ├── Acme_Enterprise_AI_Strategy_2025.txt
│       ├── Acme_Security_and_Governance_Standards.txt
│       └── Acme_Market_Expansion_Brief.txt
│
├── output/
│   ├── Company_Proposal_Generated.docx
│   ├── Company_Presentation_Generated.pptx
│   ├── Converted_From_Proposal.pptx
│   └── Converted_From_Presentation.docx
│
├── versions/
│
└── tests/
    └── test_all.py
```

---

## 🛠️ Installation & Usage

### Prerequisites

- Python 3
- Dependencies listed in `requirements.txt`

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the End-to-End Demo

```bash
python3 app.py --demo
```

### 3. Launch the Web Chatbot & REST Server

```bash
python3 app.py --server --port 8080
```

Open the following URL in your browser:

```text
http://localhost:8080
```

### 4. Start the Interactive Terminal Chatbot

```bash
python3 app.py --chat
```

### 5. Run the Test Suite

```bash
python3 app.py --test
```

The project documentation reports that all 11 unit and integration tests pass in under 0.1 seconds.

---

## 📡 REST API Reference

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Serves the responsive chatbot dashboard. |
| GET | `/api/health` | Returns system status and vector store statistics. |
| POST | `/api/chat` | Main orchestrator generation endpoint. Accepts a prompt. |
| POST | `/api/upload` | Uploads DOCX, PPTX, PDF, and image files. |
| POST | `/api/edit` | Applies conversational editing instructions. |
| POST | `/api/convert` | Converts between DOCX and PPTX formats. |
| GET | `/api/artifacts` | Lists generated files and their download URLs. |
| GET | `/api/download/<filename>` | Downloads generated DOCX or PPTX files. |
| GET | `/api/traceability` | Returns citation and claim lineage information. |
| GET | `/api/versions` | Returns version history and diff logs. |

### Example Request Bodies

**Chat generation — `POST /api/chat`**

```json
{
  "prompt": "Create a proposal using the uploaded template."
}
```

**Conversational editing — `POST /api/edit`**

```json
{
  "instruction": "Add an executive summary."
}
```

**Document conversion — `POST /api/convert`**

```json
{
  "direction": "docx_to_pptx"
}
```

Supported conversion directions:

- `docx_to_pptx`
- `pptx_to_docx`

---

## 📋 Project Deliverables

1. **Multi-agent chatbot POC:** CLI, REST API, and web dashboard.
2. **Modular source code:** Organized into agents, core engines, API services, and supporting scripts.
3. **Template analysis:** Extraction of typography, brand palettes, margins, layouts, and tone.
4. **Web research and Enterprise RAG:** Research capabilities and vector-based knowledge retrieval.
5. **Editable document generation:** Native OpenXML DOCX and 12-slide PPTX outputs.
6. **Conversational editing:** Refinements for executive summaries, conciseness, competitive analysis, and updated information.
7. **Citation traceability:** Provenance mapping, confidence ratings, and source references.
8. **Sample templates and outputs:** Included in the project directories.
9. **Technical documentation:** Architecture diagrams, usage instructions, and API specifications.
10. **Requirements and Git repository:** Dependency specifications and repository initialization on the `main` branch.

---

## 🧪 Testing

The project includes an automated test suite:

```bash
python3 app.py --test
```

Test file:

```text
tests/test_all.py
```

The documented test suite contains 11 unit and integration tests.

---

## 🔮 Future Enhancements

Potential areas for further development include:

- Integration with production-grade LLM APIs.
- Improved semantic embeddings and retrieval quality.
- Authentication and role-based access control.
- Enhanced OCR and complex document-layout recognition.
- More advanced template fidelity and formatting validation.
- Expanded evaluation datasets and automated quality benchmarks.
- Production deployment, monitoring, and observability.

---

## 📄 License

Add the applicable license information here before distributing the project publicly.

---

**Enterprise Multi-Agent AI System — Document & PPT Generation POC**

*Automating document intelligence, enterprise knowledge retrieval, and editable business content generation.*# Enterprise Multi-Agent AI System: Document & PPT Generation POC

An enterprise-grade multi-agent AI chatbot platform designed to understand complex user requests, analyze uploaded documents and PowerPoint templates, conduct web research, retrieve proprietary knowledge through Enterprise Vector RAG, and autonomously generate **fully editable Microsoft Word documents (.docx) and 12-slide PowerPoint presentations (.pptx)**.

The platform features:

- A Supervisor/Orchestrator coordinating 9 specialized sub-agents.
- Multi-format document ingestion, including DOCX, PPTX, PDF, and scanned images.
- OCR and vision-based document analysis.
- Template-aware document and presentation generation.
- Enterprise knowledge retrieval using vector search and RAG.
- Conversational in-place editing and bidirectional DOCX/PPTX conversion.
- Citation provenance, validation, and version management.

---

## 🏛️ System Architecture

```text
                    ┌─────────────────────────────┐
                    │       User Prompt/Input     │
                    └──────────────┬──────────────┘
                                   ▼
                    ┌─────────────────────────────┐
                    │  Supervisor / Orchestrator  │
                    └──────────────┬──────────────┘
                                   │
           ┌───────────────────────┼───────────────────────┐
           ▼                       ▼                       ▼
 ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
 │ Document Analyzer│   │   PPT Analyzer   │   │  Web Researcher  │
 │   DOCX/PDF/OCR   │   │ PPTX Templates   │   │  Real-Time Search│
 └─────────┬────────┘   └─────────┬────────┘   └─────────┬────────┘
           │                      │                      │
           └──────────────────────┼──────────────────────┘
                                  ▼
                       ┌────────────────────┐
                       │   Enterprise RAG   │
                       │  Vector DB / KB     │
                       └─────────┬──────────┘
                                 ▼
                    ┌─────────────────────────────┐
                    │      Generation Agents      │
                    ├──────────────┬──────────────┤
                    │ Doc Generator│ PPT Generator│
                    └───────┬──────┴──────┬───────┘
                            │             │
                            └──────┬──────┘
                                   ▼
                    ┌─────────────────────────────┐
                    │       Validation Agent      │
                    │   Style, QA, Grounding      │
                    └──────────────┬──────────────┘
                                   ▼
                    ┌─────────────────────────────┐
                    │ Editable DOCX & 12-Slide PPTX│
                    └──────────────┬──────────────┘
                                   ▼
                    ┌─────────────────────────────┐
                    │ Conversational Editor &     │
                    │ Conversion Engine           │
                    └─────────────────────────────┘
```

---

## 🤖 Specialized Multi-Agent Roles

| Agent | Architecture Role | Responsibility |
|---|---|---|
| Supervisor / Orchestrator | Central Controller | Decomposes tasks into execution graphs, tracks inter-agent state, enforces validation gates, and records execution traces through `AgentStepLog`. |
| Document Analysis Agent | File Inspector | Analyzes DOCX, PDF, and scanned documents. Extracts typography, color palettes, margins, heading hierarchies, and tone of voice. |
| PPT Analysis Agent | Presentation Inspector | Analyzes PowerPoint templates, slide masters, 16:9 geometries, theme palettes, layouts, and content patterns. |
| Web Research Agent | Real-Time Intelligence | Formulates search queries, gathers industry information, and produces source citations. |
| Enterprise RAG Agent | Knowledge Grounding | Retrieves proprietary policies, SLAs, and technical directives from the enterprise vector database. |
| Document Generation Agent | Word Synthesis | Generates professional Word proposals with styled headings, executive summaries, tables, and citations. |
| PPT Generation Agent | Presentation Synthesis | Generates 12-slide widescreen presentations with structured layouts, dashboards, diagrams, roadmaps, and citations. |
| Validation Agent | QA & Compliance | Validates OpenXML integrity, slide count, template styling, and citation coverage. |
| Conversational Editing Agent | In-Place Refinement | Applies natural-language editing instructions while preserving the existing design system. |
| Conversion Agent | Format Translation | Converts Word proposals to PowerPoint decks and PowerPoint decks to Word reports. |

---

## 📂 Core Engine Capabilities

### 1. Native OpenXML Engine

The platform uses a Python-based OpenXML builder and parser:

- `core/ooxml_docx.py`
- `core/ooxml_pptx.py`

It generates editable DOCX and PPTX files compatible with Microsoft Office 365, LibreOffice, and Google Docs without requiring desktop Office binaries.

### 2. Multi-Format Ingestion & Vision OCR

Supported document formats:

| Format | Processing |
|---|---|
| DOCX | Parses XML packages, styles, headings, tables, and formatting. |
| PPTX | Extracts slide masters, layouts, theme colors, and presentation structure. |
| PDF | Uses a custom parser to extract text operators and document structure. |
| PNG, JPG, TIFF | Uses the vision/OCR processing module to inspect layout zones and extract textual content. |

Core modules:

- `core/pdf_parser.py`
- `core/ocr_vision.py`

### 3. Enterprise Vector RAG & Local Embedding Engine

The retrieval system includes:

- **Pinecone-compatible architecture:** Modular adapter for enterprise cloud Pinecone instances.
- **Dense vector search:** NumPy-based semantic search using hashed n-gram tokenization.
- **Similarity scoring:** L2 normalization and cosine similarity.
- **Sliding-window chunking:** 400-character chunks with 80-character overlap.
- **Persistent storage:** SQLite-backed knowledge storage.

Core module: `core/vector_store.py`

### 4. Source Traceability & Versioning

The system provides:

- Citation tags such as `[Web-1]` and `[RAG-1]`.
- Reference URLs, supporting evidence, confidence scores, and timestamps.
- Version snapshots such as `v1.0`, `v1.1`, and `v2.0`.
- Unified diff calculation and changelog audit logging.

Core modules:

- `core/version_manager.py`
- `core/citation_tracker.py`

---

## 🚀 Example Workflow & Verification

The end-to-end demonstration is implemented through `demo_workflow.py` and `tests/test_all.py`.

### Step 1: Template Analysis

The Document Analyzer and PPT Analyzer inspect uploaded templates.

**Sample DOCX analysis:**

- Primary font: Georgia
- Palette: Navy `#1B365D`, Cyan `#00A3E0`
- Tone: Executive, strategic, analytical, and formal
- Tone score: 0.95

**Sample PPTX analysis:**

- Master: 16:9 widescreen
- Dimensions: `12192000 × 6858000 EMU`
- Font: Arial
- Palette: Navy `#0F2D59`, Blue `#2563EB`, Emerald `#10B981`

### Step 2: User Request Processing

Example prompt:

> Research the latest Generative AI trends and create a proposal and 12-slide presentation using the same tone and style as the uploaded files.

The Supervisor decomposes the request into a multi-stage execution graph.

Generated artifacts:

- `output/Company_Proposal_Generated.docx`
- `output/Company_Presentation_Generated.pptx`

### Step 3: Validation

The Validation Agent checks:

- OpenXML integrity
- Presentation slide count
- Citation coverage
- Template style adherence

**Reported demonstration results:**

- Quality score: 100.0%
- OpenXML integrity: PASS
- Slide count: 12 — PASS
- Citations: 7 — PASS

### Step 4: Citation Traceability

Example sources recorded in the demonstration:

- `[Web-1]` Gartner Top Strategic Technology Trends 2025
- `[Web-2]` McKinsey Global Institute: Economic Potential of Generative AI in 2025
- `[Web-3]` Stanford AI Index 2024
- `[Web-4]` MIT Technology Review: Domain-Specific Small Language Models
- `[Web-5]` IDC Enterprise AI Governance and EU AI Act Implementation Framework
- `[RAG-1]` Acme Enterprise AI Strategy 2025

### Step 5: Conversational Refinements

| User Instruction | Demonstrated Action |
|---|---|
| Add an executive summary. | Adds an executive summary callout to the DOCX and a summary slide to the PPTX. |
| Make the presentation more concise. | Condenses slide bullets by 40%. |
| Add a competitive analysis section. | Adds a five-column competitive matrix to the DOCX and PPTX. |
| Update the report using the latest web information. | Runs a fresh web query, updates information, and advances the version to v2.0. |

### Step 6: Bidirectional Conversion

The conversion engine supports:

- DOCX proposal → 16:9 PowerPoint presentation
- PPTX presentation → narrative Word report

Example outputs:

- `output/Converted_From_Proposal.pptx`
- `output/Converted_From_Presentation.docx`

---

## 📁 Repository Structure

```text
multi_agent_doc_ppt/
│
├── app.py
├── demo_workflow.py
├── requirements.txt
├── README.md
├── knowledge_store.db
│
├── agents/
│   ├── supervisor.py
│   ├── document_analyzer.py
│   ├── ppt_analyzer.py
│   ├── web_researcher.py
│   ├── rag_agent.py
│   ├── doc_generator.py
│   ├── ppt_generator.py
│   ├── validator.py
│   ├── conversational_editor.py
│   └── converter.py
│
├── core/
│   ├── models.py
│   ├── ooxml_docx.py
│   ├── ooxml_pptx.py
│   ├── pdf_parser.py
│   ├── ocr_vision.py
│   ├── vector_store.py
│   ├── version_manager.py
│   └── citation_tracker.py
│
├── api/
│   ├── server.py
│   └── web_ui.py
│
├── templates_and_samples/
│   ├── Company_Proposal.docx
│   ├── Company_Template.pptx
│   ├── Scanned_Architecture_Brief.png
│   ├── create_samples.py
│   └── knowledge_base/
│       ├── Acme_Enterprise_AI_Strategy_2025.txt
│       ├── Acme_Security_and_Governance_Standards.txt
│       └── Acme_Market_Expansion_Brief.txt
│
├── output/
│   ├── Company_Proposal_Generated.docx
│   ├── Company_Presentation_Generated.pptx
│   ├── Converted_From_Proposal.pptx
│   └── Converted_From_Presentation.docx
│
├── versions/
│
└── tests/
    └── test_all.py
```

---

## 🛠️ Installation & Usage

### Prerequisites

- Python 3
- Dependencies listed in `requirements.txt`

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the End-to-End Demo

```bash
python3 app.py --demo
```

### 3. Launch the Web Chatbot & REST Server

```bash
python3 app.py --server --port 8080
```

Open the following URL in your browser:

```text
http://localhost:8080
```

### 4. Start the Interactive Terminal Chatbot

```bash
python3 app.py --chat
```

### 5. Run the Test Suite

```bash
python3 app.py --test
```

The project documentation reports that all 11 unit and integration tests pass in under 0.1 seconds.

---

## 📡 REST API Reference

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Serves the responsive chatbot dashboard. |
| GET | `/api/health` | Returns system status and vector store statistics. |
| POST | `/api/chat` | Main orchestrator generation endpoint. Accepts a prompt. |
| POST | `/api/upload` | Uploads DOCX, PPTX, PDF, and image files. |
| POST | `/api/edit` | Applies conversational editing instructions. |
| POST | `/api/convert` | Converts between DOCX and PPTX formats. |
| GET | `/api/artifacts` | Lists generated files and their download URLs. |
| GET | `/api/download/<filename>` | Downloads generated DOCX or PPTX files. |
| GET | `/api/traceability` | Returns citation and claim lineage information. |
| GET | `/api/versions` | Returns version history and diff logs. |

### Example Request Bodies

**Chat generation — `POST /api/chat`**

```json
{
  "prompt": "Create a proposal using the uploaded template."
}
```

**Conversational editing — `POST /api/edit`**

```json
{
  "instruction": "Add an executive summary."
}
```

**Document conversion — `POST /api/convert`**

```json
{
  "direction": "docx_to_pptx"
}
```

Supported conversion directions:

- `docx_to_pptx`
- `pptx_to_docx`

---

## 📋 Project Deliverables

1. **Multi-agent chatbot POC:** CLI, REST API, and web dashboard.
2. **Modular source code:** Organized into agents, core engines, API services, and supporting scripts.
3. **Template analysis:** Extraction of typography, brand palettes, margins, layouts, and tone.
4. **Web research and Enterprise RAG:** Research capabilities and vector-based knowledge retrieval.
5. **Editable document generation:** Native OpenXML DOCX and 12-slide PPTX outputs.
6. **Conversational editing:** Refinements for executive summaries, conciseness, competitive analysis, and updated information.
7. **Citation traceability:** Provenance mapping, confidence ratings, and source references.
8. **Sample templates and outputs:** Included in the project directories.
9. **Technical documentation:** Architecture diagrams, usage instructions, and API specifications.
10. **Requirements and Git repository:** Dependency specifications and repository initialization on the `main` branch.

---

## 🧪 Testing

The project includes an automated test suite:

```bash
python3 app.py --test
```

Test file:

```text
tests/test_all.py
```

The documented test suite contains 11 unit and integration tests.

---

## 🔮 Future Enhancements

Potential areas for further development include:

- Integration with production-grade LLM APIs.
- Improved semantic embeddings and retrieval quality.
- Authentication and role-based access control.
- Enhanced OCR and complex document-layout recognition.
- More advanced template fidelity and formatting validation.
- Expanded evaluation datasets and automated quality benchmarks.
- Production deployment, monitoring, and observability.

---

## 📄 License

Add the applicable license information here before distributing the project publicly.

---

**Enterprise Multi-Agent AI System — Document & PPT Generation POC**

*Automating document intelligence, enterprise knowledge retrieval, and editable business content generation.*
