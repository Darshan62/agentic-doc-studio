import express from "express";
import path from "path";
import fs from "fs";
import { spawn } from "child_process";
import { createServer as createViteServer } from "vite";

const app = express();
const PORT = 3000;

app.use(express.json({ limit: "50mb" }));
app.use(express.urlencoded({ extended: true, limit: "50mb" }));

// Helper to run python runner
function runPythonCommand(cmd: string, payload?: any): Promise<any> {
  return new Promise((resolve, reject) => {
    const args = ["run_pipeline.py", cmd];
    if (payload) {
      args.push(JSON.stringify(payload));
    }
    const proc = spawn("python3", args, {
      cwd: process.cwd(),
      env: { ...process.env, PYTHONPATH: "." },
    });

    let stdout = "";
    let stderr = "";

    proc.stdout.on("data", (data) => {
      stdout += data.toString();
    });

    proc.stderr.on("data", (data) => {
      stderr += data.toString();
    });

    proc.on("close", (code) => {
      if (code !== 0) {
        return reject(new Error(`Python process exited with code ${code}: ${stderr}`));
      }
      try {
        const json = JSON.parse(stdout.trim());
        resolve(json);
      } catch (err) {
        resolve({ raw_output: stdout.trim(), stderr });
      }
    });
  });
}

// API Routes
app.get("/api/health", (_req, res) => {
  res.json({ status: "ok", timestamp: new Date().toISOString() });
});

// System Status and Knowledge Base Overview
app.get("/api/status", async (_req, res) => {
  try {
    const status = await runPythonCommand("get_status");
    res.json(status);
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

// Run Multi-Agent Orchestration Pipeline
app.post("/api/orchestrate", async (req, res) => {
  try {
    const { prompt, doc_template, ppt_template } = req.body;
    const result = await runPythonCommand("orchestrate", {
      prompt: prompt || "Research the latest Generative AI trends and create a proposal and 12-slide presentation using the same tone and style as the uploaded files.",
      doc_template: doc_template || "templates_and_samples/Company_Proposal.docx",
      ppt_template: ppt_template || "templates_and_samples/Company_Template.pptx",
    });
    res.json(result);
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

// Conversational In-Place Edits
app.post("/api/conversational-edit", async (req, res) => {
  try {
    const { instruction } = req.body;
    if (!instruction) {
      return res.status(400).json({ error: "instruction is required" });
    }
    const result = await runPythonCommand("edit", { instruction });
    res.json(result);
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

// Bidirectional DOCX <-> PPTX Conversion
app.post("/api/convert", async (req, res) => {
  try {
    const { direction } = req.body; // "docx_to_pptx" or "pptx_to_docx"
    const result = await runPythonCommand("convert", { direction: direction || "docx_to_pptx" });
    res.json(result);
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

// File Upload Handler (Base64 file payload)
app.post("/api/upload", (req, res) => {
  try {
    const { filename, base64Content } = req.body;
    if (!filename || !base64Content) {
      return res.status(400).json({ error: "filename and base64Content are required" });
    }
    const uploadDir = path.join(process.cwd(), "templates_and_samples", "uploads");
    fs.mkdirSync(uploadDir, { recursive: true });
    const targetPath = path.join(uploadDir, filename);

    // Remove data URL prefix if present
    const base64Data = base64Content.replace(/^data:[^;]+;base64,/, "");
    fs.writeFileSync(targetPath, Buffer.from(base64Data, "base64"));

    res.json({
      status: "uploaded",
      filename,
      path: `templates_and_samples/uploads/${filename}`,
      size_bytes: fs.statSync(targetPath).size,
    });
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

// Download Project Zip File (Direct User Request)
app.get("/api/download-zip", async (_req, res) => {
  try {
    const zipPath = path.join(process.cwd(), "public", "downloads", "multi_agent_doc_ppt_system.zip");
    if (!fs.existsSync(zipPath)) {
      await runPythonCommand("package_zip");
    }
    res.download(zipPath, "multi_agent_doc_ppt_system.zip");
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

// Download DOCX
app.get("/api/download/docx", (_req, res) => {
  const filePath = path.join(process.cwd(), "output", "Company_Proposal_Generated.docx");
  if (fs.existsSync(filePath)) {
    res.download(filePath, "Company_Proposal_Generated.docx");
  } else {
    res.status(404).json({ error: "Generated DOCX not found. Please run orchestration first." });
  }
});

// Download PPTX
app.get("/api/download/pptx", (_req, res) => {
  const filePath = path.join(process.cwd(), "output", "Company_Presentation_Generated.pptx");
  if (fs.existsSync(filePath)) {
    res.download(filePath, "Company_Presentation_Generated.pptx");
  } else {
    res.status(404).json({ error: "Generated PPTX not found. Please run orchestration first." });
  }
});

// Download Converted Artifact
app.get("/api/download/converted", (req, res) => {
  const file = req.query.file as string;
  const filePath = path.join(process.cwd(), file || "output/Converted_From_Proposal.pptx");
  if (fs.existsSync(filePath)) {
    res.download(filePath, path.basename(filePath));
  } else {
    res.status(404).json({ error: "File not found" });
  }
});

// Static public directory serving (including downloads)
app.use(express.static(path.join(process.cwd(), "public")));

// Vite Middleware Setup
async function startServer() {
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (_req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`Enterprise Multi-Agent POC Server running on http://0.0.0.0:${PORT}`);
  });
}

startServer();
