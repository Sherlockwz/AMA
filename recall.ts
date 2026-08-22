import type { OpenClawPluginApi } from "openclaw/plugin-sdk";
import type { AMABackend } from "./backend/base.ts";
import type { AMAConfig, RetrievalPayload } from "./types.ts";

function sanitizeQuery(input: string): string {
  return input.replace(/\s+/g, " ").trim();
}

function formatSection(title: string, items: Array<{ content?: string }>): string {
  if (items.length === 0) return "";
  const lines = items.map((item, index) => `${index + 1}. ${item.content ?? ""}`);
  return `${title}:\n${lines.join("\n")}`;
}

function formatRetrievalsForInjection(retrievals: RetrievalPayload): string {
  if (Array.isArray(retrievals)) {
    const section = formatSection(
      "Retrieved Memories",
      retrievals.map((item) => ({ content: item.content })),
    );
    return section || "No AMA memories found.";
  }

  const sections = [
    formatSection(
      "Text Matches",
      (retrievals.text_match_results ?? []).map((item) => ({
        content: item.content,
      })),
    ),
    formatSection(
      "Fact Matches",
      (retrievals.fact_match_results ?? []).map((item) => ({
        content: item.content,
      })),
    ),
    formatSection(
      "Episodes",
      (retrievals.episodes_results ?? []).map((item) => ({
        content: item.content,
      })),
    ),
  ].filter(Boolean);

  return sections.length > 0 ? sections.join("\n\n") : "No AMA memories found.";
}

async function withTimeout<T>(promise: Promise<T>, timeoutMs: number): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const timer = setTimeout(() => {
      reject(new Error(`Timed out after ${timeoutMs}ms`));
    }, timeoutMs);
    promise.then(
      (value) => {
        clearTimeout(timer);
        resolve(value);
      },
      (error) => {
        clearTimeout(timer);
        reject(error);
      },
    );
  });
}

export function registerRecallHook(params: {
  api: OpenClawPluginApi;
  backend: AMABackend;
  cfg: AMAConfig;
  ensureInitialized: (userId?: string) => Promise<void>;
  resolveUserId: (params?: { userId?: string }) => string;
}) {
  const { api, backend, cfg, ensureInitialized, resolveUserId } = params;
  if (!cfg.autoRecall) {
    api.logger.info("[ama] autoRecall disabled; before_prompt_build hook not registered");
    return;
  }

  api.on(
    "before_prompt_build",
    async (event) => {
      const query = sanitizeQuery(event.prompt);
      if (!query) return;

      const userId = resolveUserId();

      try {
        await ensureInitialized(userId);
        const result = await withTimeout(
          backend.forwardRetrieve({
            user: userId,
            userInput: query,
            strongRetrieve: false,
            showUsage: false,
          }),
          8_000,
        );

        const injected = formatRetrievalsForInjection(result.retrievals);
        if (!injected || injected === "No AMA memories found.") {
          return;
        }

        return {
          prependContext: `<ama-memories>\n${injected}\n</ama-memories>`,
        };
      } catch (error) {
        api.logger.warn(`[ama] autoRecall skipped: ${String(error)}`);
        return;
      }
    },
    { priority: 0 },
  );
}

