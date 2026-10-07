# Demo Script

## Preparation
1. Ensure Ollama is running (`ollama serve`) and models are pulled (`qwen3:4b`). OR ensure `AI_PROVIDER=gemini` and `GEMINI_API_KEY` is set in `.env`.
2. Open terminal in the project root.
3. Start the application:
   ```bash
   npm run dev
   ```
4. Open the browser to `http://127.0.0.1:3000`.

## Script

**1. Context Setting**
"Welcome to the Enterprise Multi-Agent AI System. Today we're going to see how our AI creates fully editable corporate documents and presentations, perfectly formatted to our brand guidelines, using our internal knowledge base."

**2. Template Upload**
- Navigate to the UI.
- Explain: "First, I'll upload our corporate Word and PowerPoint templates. The Analysis Agents will extract our fonts, colors, and layouts."
- *Action*: Upload `Company_Proposal.docx` and `Company_Template.pptx`.

**3. Knowledge Base Upload**
- Explain: "I'll also upload some internal PDFs and scanned notes. This builds our enterprise RAG database."
- *Action*: Upload sample PDFs.

**4. Generation Request**
- *Action*: Type in the chat: "Research the latest Generative AI trends and create a proposal and 12-slide presentation using the same tone and style as the uploaded files."
- Explain: "Behind the scenes, the Supervisor routes this to 9 agents. The Web Researcher searches Google, the RAG agent retrieves internal docs, and the Writer synthesizes it. Finally, the OpenXML engines build the files deterministically."

**5. Showcase Results**
- The preview pane updates with the generated `.docx` and `.pptx`.
- *Action*: Point out the colors (e.g., Navy Blue, Georgia font) matching the original template.
- *Action*: Point out the inline citations (`[Web-1]`, `[RAG-1]`).

**6. Conversational Editing**
- Explain: "Often AI generates a PDF you can't edit. Here, we can talk to our document."
- *Action*: Click on a specific paragraph in the preview.
- *Action*: Type in the chat: "Make this paragraph bold and red."
- Explain: "The Conversational Editing Agent translates this to a rigid JSON command, and the Python engine edits the OpenXML directly."

**7. Undo / Versioning**
- *Action*: Click the "Undo" or Version history button to show it reverting perfectly.
- Explain: "Every edit is a snapshot. We can rollback anytime."

**8. Download**
- *Action*: Click "Download" on the `.pptx`.
- *Action*: Open it in Microsoft PowerPoint to prove it is a native, editable, perfectly formatted file.
