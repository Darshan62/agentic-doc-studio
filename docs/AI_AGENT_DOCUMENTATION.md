# AI Agent Documentation

The system orchestrates a pipeline of 9 specialized agents. 
**Note**: "Multi-agent" here refers to decoupled modules with specific responsibilities in a sequential pipeline, rather than independently autonomous agents communicating asynchronously.

## 1. Supervisor / Orchestrator Agent
- **Purpose**: Controls the execution graph and manages shared state.
- **Implementation**: `agents/supervisor.py`
- **Execution**: Sequential deterministic pipeline (not a dynamic LLM planner).
- **Responsibilities**: Calls sub-agents in order, passes outputs as inputs, creates version snapshots.

## 2. Document Analysis Agent
- **Purpose**: Inspects DOCX/PDF files.
- **Implementation**: `agents/document_analyzer.py`
- **Responsibilities**: Extracts typography, brand colors, margins, and headings to build a `DocumentStyle`.

## 3. PPT Analysis Agent
- **Purpose**: Inspects PPTX templates.
- **Implementation**: `agents/ppt_analyzer.py`
- **Responsibilities**: Analyzes slide masters, 16:9 geometries, and theme palettes.

## 4. Web Research Agent
- **Purpose**: Real-time intelligence gathering.
- **Implementation**: `agents/web_researcher.py`
- **Logic**: Uses Gemini's Google Search grounding feature. When running under the default Ollama provider, this agent gracefully skips live search and relies purely on the internal RAG.

## 5. Enterprise RAG Agent
- **Purpose**: Knowledge grounding.
- **Implementation**: `agents/rag_agent.py`
- **Logic**: Queries `EnterpriseVectorStore` for top-K relevant chunks to inject into the writer's context.

## 6. Content Writer Agent
- **Purpose**: Synthesizes final text.
- **Implementation**: `agents/content_writer.py`
- **Logic**: Merges web research, RAG chunks, and user prompt to formulate a structured JSON representation of a document and a presentation.

## 7. Document & PPT Generation Agents
- **Purpose**: Artifact synthesis.
- **Implementation**: `agents/doc_generator.py`, `agents/ppt_generator.py`
- **Logic**: Purely deterministic (no LLM). Maps the writer's structured JSON to the OpenXML engines to create the actual `.docx` and `.pptx` files.

## 8. Validation Agent
- **Purpose**: QA & Compliance.
- **Implementation**: `agents/validator.py`
- **Logic**: Checks generated XML for integrity, verifies slide counts, and confirms citation formatting.

## 9. Conversational Editing Agent
- **Purpose**: In-place artifact refinement.
- **Implementation**: `agents/edit_intent_parser.py`, `core/edit_schema.py`
- **Logic**: LLM maps natural language to a rigid JSON command schema; a deterministic engine executes the edits.

## Production Evolution
To scale to enterprise levels, the Supervisor should be refactored into a DAG-based orchestration engine like LangGraph, allowing parallel execution of RAG and Web Research, and dynamic task planning.
