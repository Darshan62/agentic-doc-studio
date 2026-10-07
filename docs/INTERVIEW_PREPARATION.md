# Interview Preparation

**Q1: What problem does your project solve?**
*Answer:* It automates corporate document and presentation creation while preserving exact company templates. Standard LLMs output uneditable text or PDFs; this system solves that by natively building editable `.docx` and `.pptx` files using OpenXML.

**Q2: Why multi-agent?**
*Answer:* Decomposing the problem into specialized agents (Analysis, Research, Retrieval, Generation, Validation, Editing) allows for tight control, modularity, and deterministic fallback. Instead of asking one large LLM to do everything, specific tasks are isolated, tested, and validated.

**Q3: Why RAG?**
*Answer:* Enterprise documents need factual grounding based on proprietary internal knowledge, not just the pre-trained weights of the LLM. RAG injects the precise internal corporate policies or data into the generation context, significantly reducing hallucinations.

**Q4: Why not let the LLM edit the DOCX directly?**
*Answer:* LLMs are probabilistic and struggle to perfectly format complex, strict XML schemas like OpenXML. If an LLM generates raw `.docx` XML, one missing tag corrupts the entire file. We decouple intent (LLM generating JSON commands) from execution (Python code deterministicly modifying XML).

**Q5: How does conversational editing work?**
*Answer:* A user selects a paragraph and says "Make this red". The frontend passes the object ID and instruction to the backend. The LLM translates this to `{action: "update_style", target: {type: "paragraph", id: "p123"}, changes: {color: "FF0000"}}`. A deterministic Python function then executes that exact edit in the XML.

**Q6: How do you preserve formatting?**
*Answer:* The Analysis agents parse the uploaded `.docx`/`.pptx` templates to extract colors, fonts, and layouts into a `DocumentStyle` object. The Generation agents apply these exact rules when constructing the new OpenXML packages.

**Q7: How do citations work?**
*Answer:* `CitationTracker` assigns an ID (like `[Web-1]` or `[RAG-1]`) to every retrieved snippet. The prompt forces the LLM to use these tags inline. The Validation agent ensures that sources exist and are mapped properly.

**Q8: How would you make this production-ready?**
*Answer:* Transition to a FastAPI microservice architecture, replace SQLite vector storage with Pinecone or pgvector, integrate proper Authentication/RBAC, store artifacts in S3, use a queue like Celery for async generation, and implement robust OpenTelemetry observability.
