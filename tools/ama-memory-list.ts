import { Type } from "typebox";
import type { AnyAgentTool } from "openclaw/plugin-sdk";
import type { ToolDeps } from "./index.ts";

export function createAmaMemoryListTool(deps: ToolDeps): AnyAgentTool {
  const { ensureInitialized, resolveUserId } = deps;

  return {
    name: "ama_memory_list",
    label: "AMA Memory List",
    description: "Show AMA memory statistics for a user.",
    parameters: Type.Object({
      userId: Type.Optional(
        Type.String({
          description: "Optional AMA user id override.",
        }),
      ),
    }),
    async execute(_toolCallId, params) {
      const input = params as Record<string, unknown>;
      const userId = resolveUserId({
        userId: typeof input.userId === "string" ? input.userId : undefined,
      });
      await ensureInitialized(userId);

      const stats = await deps.backend.stats(userId);
      return {
        content: [
          {
            type: "text",
            text:
              `AMA stats for ${userId}:\n` +
              `- dialogue records: ${stats.records.dialogues}\n` +
              `- facts: ${stats.records.facts}\n` +
              `- episodes: ${stats.records.episodes}\n` +
              `- sentences: ${stats.records.sentences}\n` +
              `- memory window items: ${stats.memoryWindowSize}`,
          },
        ],
        details: stats,
      };
    },
  };
}
