import "dotenv/config";
import express, { NextFunction, Request, Response } from "express";
import path from "path";
import fs from "fs";
import { spawn } from "child_process";
import { createServer as createViteServer } from "vite";

const app = express();
const PORT = 3000;
const HOST = "127.0.0.1"; // local only: the API has no login, so don't expose it to the network
const MAX_UPLOAD_MB = 25;

const ROOT = process.cwd();
const UPLOAD_DIR = path.join(ROOT, "templates_and_samples", "uploads");
const TEMPLATE_DIR = path.join(ROOT, "templates_and_samples");
const OUTPUT_DIR = path.join(ROOT, "output");
const ALLOWED_UPLOADS = [".pdf", ".docx", ".pptx", ".txt", ".md", ".png", ".jpg", ".jpeg"];
// Files the pipeline can read as knowledge (a .pptx upload is only used as a style template)
const INGESTIBLE = [".pdf", ".docx", ".txt", ".md", ".png", ".jpg", ".jpeg"];

// base64 makes files ~33% bigger, so the JSON limit is a bit above the file limit
app.use(express.json({ limit: `${Math.ceil(MAX_UPLOAD_MB * 1.4)}mb` }));

// The Python bridge always prints one JSON object; on failure it has an "error" field
type PythonResult = Record<string, unknown> & { error?: string };

// Runs `python run_pipeline.py <command> <json>` and returns its JSON output
function runPython(command: string, payload: object = {}): Promise<PythonResult> {
  return new Promise((resolve, reject) => {
    const pythonBin = process.platform === "win32" ? "python" : "python3";
    const proc = spawn(pythonBin, ["run_pipeline.py", command, JSON.stringify(payload)], {
      cwd: ROOT,
      env: { ...process.env, PYTHONPATH: "." },
    });

    let stdout = "";
    let stderr = "";
    proc.stdout.on("data", (data) => (stdout += data.toString()));
    proc.stderr.on("data", (data) => (stderr += data.toString()));

    proc.on("close", (code) => {
      let result: PythonResult | null = null;
      try {
        result = JSON.parse(stdout.trim());
      } catch {
        // stdout wasn't JSON: Python crashed before printing
      }
      if (code === 0 && result) return resolve(result);
      if (stderr) console.error(`[python ${command}]`, stderr);
      reject(new Error(result?.error || "The Python pipeline failed. Check the server log."));
    });
  });
}

// Resolves a user-supplied path and makes sure it stays inside `baseDir` (blocks ../ tricks)
function safePath(baseDir: string, userPath: string): string | null {
  const full = path.resolve(ROOT, userPath);
  return full.startsWith(baseDir + path.sep) && fs.existsSync(full) ? full : null;
}

function sendError(res: Response, err: unknown, status = 500) {
  res.status(status).json({ error: err instanceof Error ? err.message : String(err) });
}

app.get("/api/status", async (_req, res) => {
  try {
    res.json(await runPython("get_status"));
  } catch (err) {
    sendError(res, err);
  }
});

app.post("/api/orchestrate", async (req, res) => {
  const { prompt, doc_template, ppt_template } = req.body;
  if (!prompt?.trim()) return sendError(res, new Error("prompt is required"), 400);

  const docTemplate = safePath(TEMPLATE_DIR, doc_template || "templates_and_samples/Company_Proposal.docx");
  const pptTemplate = safePath(TEMPLATE_DIR, ppt_template || "templates_and_samples/Company_Template.pptx");
  if (!docTemplate?.endsWith(".docx") || !pptTemplate?.endsWith(".pptx")) {
    return sendError(res, new Error("Templates must be an existing .docx and .pptx"), 400);
  }

  try {
    res.json(await runPython("orchestrate", { prompt, doc_template: docTemplate, ppt_template: pptTemplate }));
  } catch (err) {
    sendError(res, err);
  }
});

app.post("/api/conversational-edit", async (req, res) => {
  const { instruction } = req.body;
  if (!instruction?.trim()) return sendError(res, new Error("instruction is required"), 400);
  try {
    res.json(await runPython("edit", { instruction }));
  } catch (err) {
    sendError(res, err);
  }
});

app.post("/api/convert", async (req, res) => {
  const direction = req.body.direction === "pptx_to_docx" ? "pptx_to_docx" : "docx_to_pptx";
  try {
    res.json(await runPython("convert", { direction }));
  } catch (err) {
    sendError(res, err);
  }
});

app.post("/api/search", async (req, res) => {
  const { query } = req.body;
  if (!query?.trim()) return sendError(res, new Error("query is required"), 400);
  try {
    res.json(await runPython("search", { query }));
  } catch (err) {
    sendError(res, err);
  }
});

// Upload = save the file, then index it into the knowledge base so generation can use it
app.post("/api/upload", async (req, res) => {
  const { filename, base64Content } = req.body;
  if (!filename || !base64Content) {
    return sendError(res, new Error("filename and base64Content are required"), 400);
  }

  // basename() strips any folder parts, so "../../x" can't escape the upload folder
  const safeName = path.basename(String(filename));
  const extension = path.extname(safeName).toLowerCase();
  if (!ALLOWED_UPLOADS.includes(extension)) {
    return sendError(res, new Error(`File type ${extension || "(none)"} is not supported`), 400);
  }

  try {
    fs.mkdirSync(UPLOAD_DIR, { recursive: true });
    const targetPath = path.join(UPLOAD_DIR, safeName);
    const base64Data = String(base64Content).replace(/^data:[^;]+;base64,/, "");
    fs.writeFileSync(targetPath, Buffer.from(base64Data, "base64"));

    const relativePath = `templates_and_samples/uploads/${safeName}`;
    const ingest = INGESTIBLE.includes(extension) ? await runPython("ingest", { path: targetPath }) : null;
    res.json({ status: "uploaded", filename: safeName, path: relativePath, ingest });
  } catch (err) {
    sendError(res, err);
  }
});

app.get("/api/download-zip", async (_req, res) => {
  try {
    // Rebuilt every time so the zip always matches the current code
    const { zip_path } = await runPython("package_zip");
    res.download(path.join(ROOT, String(zip_path)), "multi_agent_doc_ppt_system.zip");
  } catch (err) {
    sendError(res, err);
  }
});

// Downloads are limited to files inside output/
app.get("/api/download/:name", (req, res) => {
  const shortcuts: Record<string, string> = {
    docx: "Company_Proposal_Generated.docx",
    pptx: "Company_Presentation_Generated.pptx",
  };
  const fileName = shortcuts[req.params.name] ?? path.basename(String(req.query.file || ""));
  const filePath = safePath(OUTPUT_DIR, path.join("output", fileName));
  if (!filePath) return sendError(res, new Error("File not found. Generate it first."), 404);
  res.download(filePath, fileName);
});

// ---------- AI editor workspace (chat on the left, live DOCX/PPTX preview on the right) ----------
const WORKSPACE_DIR = path.join(OUTPUT_DIR, "workspace");
const WORKSPACE_UPLOADS = [".docx", ".pptx", ".png", ".jpg", ".jpeg", ".gif"];
const MAX_CHAT_CHARS = 2000;

// Workspace calls run one at a time, so two quick edits can't race on the same file and state.json
let workspaceQueue: Promise<unknown> = Promise.resolve();
function runWorkspace(op: string, payload: object = {}): Promise<PythonResult> {
  const next = workspaceQueue.then(() => runPython("workspace", { op, ...payload }));
  workspaceQueue = next.catch(() => undefined);
  return next;
}

// A result without `state` is a request-level problem (bad input); with `state` the chat already explains it
async function sendWorkspace(res: Response, op: string, payload: object = {}) {
  try {
    const result = await runWorkspace(op, payload);
    res.status(result.status === "error" && !result.state ? 400 : 200).json(result);
  } catch (err) {
    sendError(res, err);
  }
}

app.get("/api/workspace/state", (_req, res) => sendWorkspace(res, "state"));
app.get("/api/workspace/artifacts", (_req, res) => sendWorkspace(res, "list"));

app.post("/api/workspace/open", (req, res) => {
  const filePath = String(req.body.path || "");
  const extension = path.extname(filePath).toLowerCase();
  if (![".docx", ".pptx"].includes(extension) || !safePath(ROOT, filePath)) {
    return sendError(res, new Error("Pick an existing .docx or .pptx file."), 400);
  }
  sendWorkspace(res, "open", { path: filePath });
});

app.post("/api/workspace/upload", (req, res) => {
  const { filename, base64Content } = req.body;
  if (!filename || !base64Content) return sendError(res, new Error("filename and base64Content are required"), 400);
  const safeName = path.basename(String(filename));
  const extension = path.extname(safeName).toLowerCase();
  if (!WORKSPACE_UPLOADS.includes(extension)) {
    return sendError(res, new Error("The editor accepts .docx, .pptx and .png/.jpg/.gif images."), 400);
  }
  try {
    fs.mkdirSync(UPLOAD_DIR, { recursive: true });
    const base64Data = String(base64Content).replace(/^data:[^;]+;base64,/, "");
    fs.writeFileSync(path.join(UPLOAD_DIR, safeName), Buffer.from(base64Data, "base64"));
  } catch (err) {
    return sendError(res, err);
  }
  sendWorkspace(res, "upload", { path: `templates_and_samples/uploads/${safeName}` });
});

app.post("/api/workspace/chat", (req, res) => {
  const message = typeof req.body.message === "string" ? req.body.message.trim() : "";
  if (!message) return sendError(res, new Error("Type an instruction first."), 400);
  if (message.length > MAX_CHAT_CHARS) return sendError(res, new Error(`Keep messages under ${MAX_CHAT_CHARS} characters.`), 400);
  const currentSlide = Number.isInteger(req.body.current_slide) ? req.body.current_slide : 1;
  sendWorkspace(res, "chat", { message, selection: req.body.selection ?? null, current_slide: currentSlide });
});

for (const op of ["undo", "redo", "clear"]) {
  app.post(`/api/workspace/${op}`, (_req, res) => sendWorkspace(res, op));
}

app.post("/api/workspace/restore", (req, res) => {
  const version = String(req.body.version || "");
  if (!/^v\d+\.\d+$/.test(version)) return sendError(res, new Error("Unknown version."), 400);
  sendWorkspace(res, "restore", { version });
});

// Serves the edited working copy (the exact bytes the preview was built from)
app.get("/api/workspace/download", (_req, res) => {
  try {
    const state = JSON.parse(fs.readFileSync(path.join(WORKSPACE_DIR, "state.json"), "utf-8"));
    const active = state?.active;
    const filePath = active ? safePath(WORKSPACE_DIR, String(active.working_path)) : null;
    if (!filePath) return sendError(res, new Error("Open a document first."), 404);
    res.setHeader("Cache-Control", "no-store");
    res.download(filePath, path.basename(String(active.name)));
  } catch {
    sendError(res, new Error("Open a document first."), 404);
  }
});

// Turns body-parser errors (e.g. file too large) into JSON instead of an HTML page
app.use("/api", (err: { type?: string; status?: number }, _req: Request, res: Response, _next: NextFunction) => {
  if (err?.type === "entity.too.large") {
    return sendError(res, new Error(`File is too large (max ${MAX_UPLOAD_MB} MB)`), 413);
  }
  sendError(res, err, err?.status || 500);
});

app.use(express.static(path.join(ROOT, "public")));

async function startServer() {
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({ server: { middlewareMode: true }, appType: "spa" });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(ROOT, "dist");
    app.use(express.static(distPath));
    app.get("*", (_req, res) => res.sendFile(path.join(distPath, "index.html")));
  }

  app.listen(PORT, HOST, () => {
    console.log(`Multi-Agent Doc/PPT server running on http://${HOST}:${PORT}`);
    if (!process.env.GEMINI_API_KEY) console.warn("GEMINI_API_KEY is not set: generation will fail.");
  });
}

startServer();
