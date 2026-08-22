import type { OpenClawPluginApi } from "openclaw/plugin-sdk";
import type { AMABackend } from "./backend/base.ts";
import type { AMAConfig } from "./types.ts";

function flattenContent(content: unknown): string {
  if (typeof content === "string") return content;
  if (Array.isArray(content)) {
    return content
      .map((item) => {
        if (!item || typeof item !== "object") return "";
        const record = item as Record<string, unknown>;
        if (typeof record.text === "string") return record.text;
        if (typeof record.thinking === "string") return "";
        return "";
      })
      .filter(Boolean)
      .join("\n");
  }
  return "";
}

function extractMessages(messages: unknown[]): Array<{ role: string; text: string }> {
  return messages
    .map((message) => {
      if (!message || typeof message !== "object") return null;
      const record = message as Record<string, unknown>;
      const role = typeof record.role === "string" ? record.role : "";
      const text = flattenContent(record.content);
      if (!role || !text.trim()) return null;
      return { role, text: text.trim() };
    })
    .filter((item): item is { role: string; text: string } => item !== null);
}

export function registerCaptureHook(params: {
  api: OpenClawPluginApi;
  backend: AMABackend;
  cfg: AMAConfig;
  ensureInitialized: (userId?: string) => Promise<void>;
  resolveUserId: (params?: { userId?: string }) => string;
}) {
  const { api, backend, cfg, ensureInitialized, resolveUserId } = params;
  if (!cfg.autoCapture) {
    api.logger.info("[ama] autoCapture disabled; agent_end hook not registered");
    return;
  }

  api.on("agent_end", (event) => {
    void (async () => {
      const parsed = extractMessages(
        Array.isArray(event.messages) ? event.messages : [],
      ).filter((message) => !message.text.includes("<ama-memories>"));

      const userMessage = [...parsed].reverse().find((message) => message.role === "user");
      const assistantMessage = [...parsed]
        .reverse()
        .find((message) => message.role === "assistant");

      if (!userMessage && !assistantMessage) return;

      const userId = resolveUserId();
      await ensureInitialized(userId);

      if (userMessage) {
        await backend.forwardUser({
          user: userId,
          userInput: userMessage.text,
          showUsage: false,
        });
      }

      if (assistantMessage) {
        await backend.forwardRobot({
          user: userId,
          robotOutput: assistantMessage.text,
          showUsage: false,
        });
      }

      await backend.judgeAndGenerate(userId);
    })().catch((error) => {
      api.logger.warn(`[ama] autoCapture failed: ${String(error)}`);
    });
  });
}

