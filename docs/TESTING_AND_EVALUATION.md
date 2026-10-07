# Testing & Evaluation Documentation

## Current Test Suite

The current test suite is implemented in Python `unittest`.
Tests are located in `tests/`:
- `test_edit_engine.py`
- `test_edit_operations.py`
- `test_editor_workspace.py`
- `test_llm_client.py`
- `test_multi_agent_system.py`

**Test Execution**: `python -m unittest discover tests`

### Test Coverage Highlights
- **Mocked LLM**: The test suite mocks LLM outputs to ensure deterministic, fast execution without requiring API keys or incurring costs.
- **Temporary Execution**: Tests run in temp folders to prevent side-effects on the main `output/` directory.
- **OpenXML Tests**: Thorough checks on OpenXML packaging, ZIP integrity, style mapping, and relationships.

## AI Evaluation Strategy (Enterprise Recommendation)

Traditional unit tests are insufficient for stochastic LLM outputs. An enterprise system requires offline LLM evaluation metrics:

### 1. RAG Evaluation Metrics
- **Recall@K**: Is the required knowledge in the top-K retrieved chunks?
- **MRR / nDCG**: Is the best chunk ranked at the top?

### 2. Generation Evaluation Metrics
- **Faithfulness**: Are the claims in the generated document entirely supported by the retrieved context (no hallucinations)?
- **Completeness**: Did the document answer the user's entire prompt?
- **Citation Correctness**: Are `[RAG-1]` citations properly mapped to the exact evidence text?

### 3. OpenXML Formatting Evaluation
- **Formatting Fidelity**: Are the extracted styles (e.g., `#1B365D`) accurately present in the raw `<w:color w:val="1B365D"/>` tags of the generated `.docx`?
- **Slide Count Validity**: Does the PPT generation strictly output the required 12 slides?

Use frameworks like `ragas`, `truera`, or `deepeval` in the CI/CD pipeline to benchmark generation quality against a golden dataset of ~200 prompt-document pairs.
