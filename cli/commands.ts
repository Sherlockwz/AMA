import type { OpenClawPluginApi } from "openclaw/plugin-sdk";
import type { AMABackend } from "../backend/base.ts";
import type { AMAConfig } from "../types.ts";

function printSetupGuide(api: OpenClawPluginApi) {
  api.logger.info(
    [
      "[ama] setup required",
      "Required environment variables:",
      "  AMA_LLM_API_KEY",
      "  AMA_LLM_BASE_URL",
      "  AMA_EMBEDDING_URL",
      "Example values for the OpenAI API:",
      "  AMA_LLM_BASE_URL=https://api.openai.com/v1/chat/completions",
      "  AMA_EMBEDDING_URL=https://api.openai.com/v1/embeddings",
      "Useful commands:",
      "  openclaw ama doctor",
      "  openclaw ama setup",
    ].join("\n"),
  );
}

async function ensureReady(params: {
  api: OpenClawPluginApi;
  cfg: AMAConfig;
  backend: AMABackend;
  ensureInitialized: (userId?: string) => Promise<void>;
  userId: string;
}): Promise<boolean> {
  const { api, cfg, backend, ensureInitialized, userId } = params;
  if (cfg.needsSetup) {
    printSetupGuide(api);
    return false;
  }

  await ensureInitialized(userId);

  try {
    const healthy = await backend.health();
    if (!healthy) {
      api.logger.warn("[ama] sidecar did not report healthy status");
    }
  } catch (error) {
    api.logger.warn(`[ama] sidecar health check failed: ${String(error)}`);
  }
  return true;
}

export function registerCliCommands(params: {
  api: OpenClawPluginApi;
  backend: AMABackend;
  cfg: AMAConfig;
  ensureInitialized: (userId?: string) => Promise<void>;
}) {
  const { api, backend, cfg, ensureInitialized } = params;

  api.registerCli(({ program }) => {
    const ama = program.command("ama").description("AMA memory commands");

    ama
      .command("setup")
      .description("Print AMA setup instructions")
      .action(() => {
        printSetupGuide(api);
        api.logger.info(
          JSON.stringify(
            {
              openclawConfigPath: "~/.openclaw/openclaw.json",
              configTemplate: {
                plugins: {
                  slots: {
                    memory: "openclaw-ama",
                  },
                  allow: ["openclaw-ama"],
                  entries: {
                    "openclaw-ama": {
                      enabled: true,
                      hooks: {
                        allowConversationAccess: true,
                      },
                      config: {
                        llmApiKey: "${AMA_LLM_API_KEY}",
                        llmBaseUrl: "${AMA_LLM_BASE_URL}",
                        embeddingApiUrl: "${AMA_EMBEDDING_URL}",
                      },
                    },
                  },
                },
              },
            },
            null,
            2,
          ),
        );
      });

    ama
      .command("doctor")
      .description("Check AMA configuration and sidecar connectivity")
      .option("--user-id <userId>", "override AMA user id")
      .action(async (options: { userId?: string }) => {
        const userId = options.userId ?? cfg.userId;
        const summary = {
          userId,
          configured: {
            llmApiKey: Boolean(cfg.llmApiKey),
            llmBaseUrl: Boolean(cfg.llmBaseUrl),
            embeddingApiUrl: Boolean(cfg.embeddingApiUrl),
          },
          values: {
            llmBaseUrl: cfg.llmBaseUrl || null,
            embeddingApiUrl: cfg.embeddingApiUrl || null,
            dataDir: cfg.dataDir,
            pythonExecutable: cfg.pythonExecutable || "auto",
            sidecarPort: cfg.sidecarPort,
            sidecarAutoStart: cfg.sidecarAutoStart,
            autoRecall: cfg.autoRecall,
            autoCapture: cfg.autoCapture,
            modelMemory: cfg.modelMemory,
          },
        };
        api.logger.info(JSON.stringify(summary, null, 2));

        if (cfg.needsSetup) {
          printSetupGuide(api);
          return;
        }

        try {
          await ensureInitialized(userId);
          const healthy = await backend.health();
          api.logger.info(
            JSON.stringify(
              {
                sidecarHealthy: healthy,
              },
              null,
              2,
            ),
          );
        } catch (error) {
          api.logger.error(`[ama] doctor failed: ${String(error)}`);
        }
      });

    ama
      .command("search")
      .description("Search AMA memory")
      .argument("<query>", "search query")
      .option("--user-id <userId>", "override AMA user id")
      .option("--strong", "enable strong retrieval")
      .action(async (query: string, options: { userId?: string; strong?: boolean }) => {
        const userId = options.userId ?? cfg.userId;
        if (
          !(await ensureReady({
            api,
            cfg,
            backend,
            ensureInitialized,
            userId,
          }))
        ) {
          return;
        }
        const result = await backend.forwardRetrieve({
          user: userId,
          userInput: query,
          strongRetrieve: options.strong === true,
          showUsage: false,
        });
        api.logger.info(JSON.stringify(result, null, 2));
      });

    ama
      .command("stats")
      .description("Show AMA memory stats")
      .option("--user-id <userId>", "override AMA user id")
      .action(async (options: { userId?: string }) => {
        const userId = options.userId ?? cfg.userId;
        if (
          !(await ensureReady({
            api,
            cfg,
            backend,
            ensureInitialized,
            userId,
          }))
        ) {
          return;
        }
        const result = await backend.stats(userId);
        api.logger.info(JSON.stringify(result, null, 2));
      });

    ama
      .command("clear")
      .description("Clear AMA memory")
      .option("--user-id <userId>", "override AMA user id")
      .action(async (options: { userId?: string }) => {
        const userId = options.userId ?? cfg.userId;
        if (
          !(await ensureReady({
            api,
            cfg,
            backend,
            ensureInitialized,
            userId,
          }))
        ) {
          return;
        }
        await backend.clearAllMemory(userId);
        api.logger.info(`Cleared AMA memory for ${userId}`);
      });
  }, { commands: ["ama"] });
}
