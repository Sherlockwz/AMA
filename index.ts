import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";
import type { OpenClawPluginApi } from "openclaw/plugin-sdk";
import { CONFIG_JSON_SCHEMA, CONFIG_UI_HINTS, parseAMAConfig } from "./config.ts";
import { SidecarBackend } from "./backend/sidecar.ts";
import { createInitParams, createRetrievalPreview, registerAllTools } from "./tools/index.ts";
import { registerRecallHook } from "./recall.ts";
import { registerCaptureHook } from "./capture.ts";
import { registerSidecarService } from "./service.ts";
import { registerCliCommands } from "./cli/commands.ts";

export default definePluginEntry({
  id: "openclaw-ama",
  name: "Memory (AMA)",
  description:
    "AMA adaptive memory for OpenClaw. Provides sidecar-backed retrieval and turn processing.",
  configSchema: {
    parse: parseAMAConfig,
    uiHints: CONFIG_UI_HINTS,
    jsonSchema: CONFIG_JSON_SCHEMA as unknown as Record<string, unknown>,
  },
  register(api: OpenClawPluginApi) {
    const cfg = parseAMAConfig(api.pluginConfig);
    const backend = new SidecarBackend(cfg.sidecarPort);

    const ensureInitialized = async (userId?: string) => {
      await backend.init(
        createInitParams(
          cfg,
          (input) => api.resolvePath(input),
          userId ?? cfg.userId,
        ),
      );
    };

    registerCliCommands({
      api,
      backend,
      cfg,
      ensureInitialized,
    });

    api.logger.info(
      cfg.needsSetup
        ? [
            "[ama] configuration incomplete; tools/hooks are not registered yet",
            "Required: AMA_LLM_API_KEY, AMA_LLM_BASE_URL, AMA_EMBEDDING_URL",
            "Example AMA_LLM_BASE_URL: https://api.openai.com/v1/chat/completions",
            "Example AMA_EMBEDDING_URL: https://api.openai.com/v1/embeddings",
            "Run `openclaw ama doctor` after configuring credentials.",
          ].join("\n")
        : `[ama] sidecar backend configured on port ${cfg.sidecarPort}`,
    );

    if (cfg.needsSetup) {
      return;
    }

    registerAllTools({
      api,
      backend,
      cfg,
      resolveUserId: (params) => params?.userId ?? cfg.userId,
      ensureInitialized,
      renderRetrievalPreview: createRetrievalPreview,
    });

    registerRecallHook({
      api,
      backend,
      cfg,
      ensureInitialized,
      resolveUserId: (params) => params?.userId ?? cfg.userId,
    });

    registerCaptureHook({
      api,
      backend,
      cfg,
      ensureInitialized,
      resolveUserId: (params) => params?.userId ?? cfg.userId,
    });

    registerSidecarService({
      api,
      backend,
      cfg,
      ensureInitialized,
    });

    void backend.health().catch((error) => {
      api.logger.warn(`[ama] sidecar health check failed: ${String(error)}`);
    });
  },
});
