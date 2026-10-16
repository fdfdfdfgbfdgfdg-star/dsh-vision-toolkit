// dsh-vision-toolkit -- eyes for text-only DeepSeek Harness agents on Windows.
//
// Registers four agent tools, all fully local (no API keys, no quotas,
// no network, no Python):
//
//   ui_screenshot   — DPI-aware capture of the Windows virtual screen
//   ui_ocr          — OCR via the built-in Windows.Media.Ocr engine
//   ui_diff         — per-pixel comparison of two images (ratio + %)
//   ui_screen_check — one-shot combo: capture -> OCR -> report
//
// Screenshots are written under <workspace>/temp/screenshots/ and are never
// deleted by this plugin (audit trail). The implementation delegates to the
// PowerShell scripts in scripts/ (capture.ps1 / ocr.ps1 / diff.ps1) executed
// with -STA -NonInteractive -NoProfile.
//
// Pure Node ESM, no runtime dependencies, no build step.

import { execFile } from "node:child_process";
import { existsSync } from "node:fs";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { promisify } from "node:util";

const run = promisify(execFile);

const HERE = dirname(fileURLToPath(import.meta.url));

export const name = "dsh-vision-toolkit";
export const inject = ["tools"];

const SCREENSHOT_DIR = path.join("temp", "screenshots");
const DEFAULT_LANG = "ru-RU";
const DEFAULT_TIMEOUT_MS = 60000;

const stringOutput = {
  schema: { type: "string" },
  render: (_args, value) => [{ type: "text", text: value }],
};

function dirname(p) {
  const i = Math.max(p.lastIndexOf("/"), p.lastIndexOf("\\"));
  return i <= 0 ? "." : p.slice(0, i);
}

function workspaceOf(exec) {
  const session = exec?.agent?.session;
  const cwd = session?.header?.cwd;
  return typeof cwd === "string" && cwd !== "" ? cwd : process.cwd();
}

function timestamp() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  return (
    d.getFullYear() +
    pad(d.getMonth() + 1) +
    pad(d.getDate()) +
    "_" +
    pad(d.getHours()) +
    pad(d.getMinutes()) +
    pad(d.getSeconds())
  );
}

function resolveWorkspacePath(workspace, requested) {
  if (typeof requested !== "string" || requested.trim() === "") return null;
  if (path.isAbsolute(requested)) return requested;
  return path.join(workspace, requested);
}

async function ensureDir(dir) {
  await mkdir(dir, { recursive: true });
}

async function runPowerShell(scriptFile, args, timeoutMs) {
  const powershell =
    process.env.DSH_VISION_TOOLKIT_PS ??
    (process.platform === "win32" ? "powershell.exe" : "pwsh");
  return run(powershell, [
    "-NoProfile",
    "-NonInteractive",
    "-STA",
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    scriptFile,
    ...args,
  ], { windowsHide: true, timeout: timeoutMs ?? DEFAULT_TIMEOUT_MS, maxBuffer: 32 * 1024 * 1024 });
}

function psQuote(value) {
  return `'${String(value).replace(/'/g, "''")}'`;
}

// ---------------------------------------------------------------------------
// capture: DPI-aware Windows virtual screen -> PNG
// ---------------------------------------------------------------------------

async function captureScreen(outputPath, timeoutMs) {
  const script = path.join(HERE, "scripts", "capture.ps1");
  if (!existsSync(script)) {
    throw new Error(`ui_screenshot: capture script not found: ${script}`);
  }
  const { stdout } = await runPowerShell(script, ["-Output", psQuote(outputPath)], timeoutMs);
  if (!existsSync(outputPath)) {
    throw new Error(
      `ui_screenshot: capture reported success but produced no file. stdout: ${String(stdout).slice(0, 300)}`
    );
  }
  return outputPath;
}

// ---------------------------------------------------------------------------
// ocr: Windows.Media.Ocr
// ---------------------------------------------------------------------------

async function ocrImage(imagePath, lang, timeoutMs) {
  const script = path.join(HERE, "scripts", "ocr.ps1");
  if (!existsSync(script)) {
    throw new Error(`ui_ocr: ocr script not found: ${script}`);
  }
  const args = ["-Image", psQuote(imagePath), "-Lang", psQuote(lang ?? DEFAULT_LANG)];
  const { stdout } = await runPowerShell(script, args, timeoutMs);
  return String(stdout ?? "").trim();
}

// ---------------------------------------------------------------------------
// diff: pixel comparison
// ---------------------------------------------------------------------------

async function diffImages(a, b, threshold, timeoutMs) {
  const script = path.join(HERE, "scripts", "diff.ps1");
  if (!existsSync(script)) {
    throw new Error(`ui_diff: diff script not found: ${script}`);
  }
  const args = ["-A", psQuote(a), "-B", psQuote(b), "-Threshold", String(threshold ?? 16), "-Json"];
  const { stdout } = await runPowerShell(script, args, timeoutMs ?? 120000);
  return String(stdout ?? "").trim();
}

// ---------------------------------------------------------------------------
// plugin
// ---------------------------------------------------------------------------

export function apply(ctx) {
  console.info(
    "[dsh-vision-toolkit] started: local screenshot/OCR/diff tools active (no keys, no quotas)"
  );

  const disposers = [];

  const register = (def) => {
    disposers.push(ctx.tools.register(def));
  };

  // -- ui_screenshot --------------------------------------------------------
  register({
    name: "ui_screenshot",
    description:
      "Capture the Windows desktop (whole virtual screen, DPI-aware) as a PNG and save it under temp/screenshots/ in the session workspace. " +
      "Fully local: no API keys, no quotas, no network. Returns the saved path and file size. " +
      "Use before/after UI changes and as final verification that an interface rendered correctly.",
    parameters: {
      type: "object",
      properties: {
        filename: {
          type: "string",
          description:
            "Optional output file name (relative to temp/screenshots/). Default: ui_<timestamp>.png",
        },
        lang: {
          type: "string",
          description:
            "Optional OCR language tag for the bundled text (default ru-RU); use en-US for English UI",
        },
        ocr: {
          type: "boolean",
          description:
            "Also run Windows OCR on the capture and include the recognized text in the result (default true)",
        },
      },
      additionalProperties: false,
    },
    output: stringOutput,
    async execute(args, exec) {
      const workspace = workspaceOf(exec);
      const dir = path.join(workspace, SCREENSHOT_DIR);
      await ensureDir(dir);
      const filename =
        typeof args.filename === "string" && args.filename.trim() !== ""
          ? args.filename.trim()
          : `ui_${timestamp()}.png`;
      const outputPath = path.join(dir, filename);

      await captureScreen(outputPath);

      const result = {
        ok: true,
        path: outputPath,
        workspaceRelativePath: path.join(SCREENSHOT_DIR, filename),
        sizeBytes: (await import("node:fs/promises")).stat(outputPath).then((s) => s.size),
      };

      if (args.ocr !== false) {
        try {
          const text = await ocrImage(outputPath, args.lang, DEFAULT_TIMEOUT_MS);
          result.ocrText = text;
          if (text && text !== "") {
            const ocrDir = path.join(dir, "ocr");
            await ensureDir(ocrDir);
            const txtName = filename.replace(/\.png$/i, "") + ".txt";
            await writeFile(path.join(ocrDir, txtName), text, "utf8");
            result.ocrFile = path.join(SCREENSHOT_DIR, "ocr", txtName);
          }
        } catch (error) {
          result.ocrError = error?.message ?? String(error);
        }
      }

      return JSON.stringify(result, null, 2);
    },
  });

  // -- ui_ocr ---------------------------------------------------------------
  register({
    name: "ui_ocr",
    description:
      "Recognize text on an image using the built-in Windows.Media.Ocr engine (local, no keys, no quotas). " +
      "Works on screenshots, photos and any PNG/JPEG. Best for extracting UI text when a vision model is unavailable or rate-limited.",
    parameters: {
      type: "object",
      properties: {
        image: {
          type: "string",
          description:
            "Image path: absolute or workspace-relative (e.g. temp/screenshots/ui_xxx.png or an attachment id resolved earlier)",
        },
        lang: {
          type: "string",
          description: "OCR language tag, default ru-RU; en-US for English text",
        },
      },
      required: ["image"],
      additionalProperties: false,
    },
    output: stringOutput,
    async execute(args, exec) {
      const workspace = workspaceOf(exec);
      const imagePath = resolveWorkspacePath(workspace, args.image);
      if (!imagePath) throw new Error("ui_ocr: image is required");
      if (!existsSync(imagePath)) {
        throw new Error(`ui_ocr: image not found: ${imagePath}`);
      }
      const text = await ocrImage(imagePath, args.lang, DEFAULT_TIMEOUT_MS);
      return JSON.stringify({ ok: true, image: imagePath, text }, null, 2);
    },
  });

  // -- ui_diff --------------------------------------------------------------
  register({
    name: "ui_diff",
    description:
      "Per-pixel comparison of two images (usually two ui_screenshot captures). " +
      "Returns the fraction of pixels that differ beyond a channel threshold. " +
      "0% = identical screens. Use to detect whether the UI actually changed after an edit, or to verify a rebuild matches a reference.",
    parameters: {
      type: "object",
      properties: {
        image_a: { type: "string", description: "First image (reference), path absolute or workspace-relative" },
        image_b: { type: "string", description: "Second image (current), path absolute or workspace-relative" },
        threshold: {
          type: "integer",
          description: "Per-channel difference tolerance 0-255, default 16",
        },
      },
      required: ["image_a", "image_b"],
      additionalProperties: false,
    },
    output: stringOutput,
    async execute(args, exec) {
      const workspace = workspaceOf(exec);
      const a = resolveWorkspacePath(workspace, args.image_a);
      const b = resolveWorkspacePath(workspace, args.image_b);
      if (!a || !b) throw new Error("ui_diff: image_a and image_b are required");
      if (!existsSync(a)) throw new Error(`ui_diff: image_a not found: ${a}`);
      if (!existsSync(b)) throw new Error(`ui_diff: image_b not found: ${b}`);
      const json = await diffImages(a, b, args.threshold, 120000);
      let report;
      try {
        report = JSON.parse(json);
      } catch {
        report = { raw: json };
      }
      return JSON.stringify({ ok: true, a, b, ...report }, null, 2);
    },
  });

  // -- ui_screen_check --------------------------------------------------------
  register({
    name: "ui_screen_check",
    description:
      "One-shot visual verification of the desktop: capture the screen, run local OCR, and return path + recognized text. " +
      "Equivalent to ui_screenshot with ocr=true. Use it as the 'final check before reporting the task complete' step: " +
      "make sure the expected interface/window is actually on screen and the expected labels are present.",
    parameters: {
      type: "object",
      properties: {
        filename: {
          type: "string",
          description: "Optional output file name under temp/screenshots/ (default: check_<timestamp>.png)",
        },
        lang: { type: "string", description: "OCR language tag, default ru-RU" },
      },
      additionalProperties: false,
    },
    output: stringOutput,
    async execute(args, exec) {
      const workspace = workspaceOf(exec);
      const dir = path.join(workspace, SCREENSHOT_DIR);
      await ensureDir(dir);
      const filename =
        typeof args.filename === "string" && args.filename.trim() !== ""
          ? args.filename.trim()
          : `check_${timestamp()}.png`;
      const outputPath = path.join(dir, filename);

      await captureScreen(outputPath);

      const result = {
        ok: true,
        path: outputPath,
        workspaceRelativePath: path.join(SCREENSHOT_DIR, filename),
        sizeBytes: (await import("node:fs/promises")).stat(outputPath).then((s) => s.size),
      };

      try {
        const text = await ocrImage(outputPath, args.lang, DEFAULT_TIMEOUT_MS);
        result.ocrText = text;
        if (text && text !== "") {
          const ocrDir = path.join(dir, "ocr");
          await ensureDir(ocrDir);
          const txtName = filename.replace(/\.png$/i, "") + ".txt";
          await writeFile(path.join(ocrDir, txtName), text, "utf8");
          result.ocrFile = path.join(SCREENSHOT_DIR, "ocr", txtName);
        }
      } catch (error) {
        result.ocrError = error?.message ?? String(error);
      }

      return JSON.stringify(result, null, 2);
    },
  });

  return () => {
    disposers.splice(0).forEach((dispose) => {
      try {
        dispose();
      } catch {
        /* best effort */
      }
    });
  };
}

export default { name, apply };
