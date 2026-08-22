import { existsSync } from "node:fs";
import { spawn, type ChildProcessWithoutNullStreams } from "node:child_process";
import path from "node:path";
import type { OpenClawPluginApi } from "openclaw/plugin-sdk";
import type { AMABackend } from "./backend/base.ts";
import type { AMAConfig } from "./types.ts";

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export function registerSidecarService(params: {
  api: OpenClawPluginApi;
  backend: AMABackend;
  cfg: AMAConfig;
  ensureInitialized: (userId?: string) => Promise<void>;
}) {
  const { api, backend, cfg, ensureInitialized } = params;
  let child: ChildProcessWithoutNullStreams | undefined;

  api.registerService({
    id: "openclaw-ama-sidecar",
    start: async () => {
      if (!cfg.sidecarAutoStart) {
        api.logger.info("[ama] sidecarAutoStart disabled; service start skipped");
        return;
      }

      if (child && !child.killed) {
        return;
      }

      const pluginRoot = api.rootDir ?? process.cwd();
      const pythonDir = path.join(pluginRoot, "python");
      const venvPython = path.join(
        pluginRoot,
        ".venv",
        process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
      );
      const pythonExecutable =
        cfg.pythonExecutable || (existsSync(venvPython) ? venvPython : "python3");

      child = spawn(
        pythonExecutable,
        ["-m", "uvicorn", "server:app", "--port", String(cfg.sidecarPort)],
        {
          cwd: pythonDir,
          env: {
            ...process.env,
            AMA_LLM_API_KEY: cfg.llmApiKey,
            AMA_LLM_BASE_URL: cfg.llmBaseUrl,
            AMA_EMBEDDING_URL: cfg.embeddingApiUrl,
          },
        },
      );

      child.stdout.on("data", (chunk) => {
        api.logger.info(`[ama-sidecar] ${String(chunk).trim()}`);
      });
      child.stderr.on("data", (chunk) => {
        api.logger.warn(`[ama-sidecar] ${String(chunk).trim()}`);
      });
      child.on("exit", (code) => {
        api.logger.warn(`[ama-sidecar] exited with code ${String(code)}`);
        child = undefined;
      });

      for (let attempt = 0; attempt < 30; attempt += 1) {
        try {
          if (await backend.health()) {
            await ensureInitialized(cfg.userId);
            api.logger.info("[ama] sidecar service is ready");
            return;
          }
        } catch {
          // ignore until ready
        }
        await sleep(500);
      }

      throw new Error("AMA sidecar did not become healthy in time");
    },
    stop: async () => {
      if (child && !child.killed) {
        child.kill("SIGTERM");
      }
      child = undefined;
    },
  });
}
