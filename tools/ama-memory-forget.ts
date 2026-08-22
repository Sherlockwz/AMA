import { Type } from "typebox";
import type { AnyAgentTool } from "openclaw/plugin-sdk";
import type { ToolDeps } from "./index.ts";

export function createAmaMemoryForgetTool(deps: ToolDeps): AnyAgentTool {
  const { ensureInitialized, resolveUserId } = deps;

  return {
    name: "ama_memory_forget",
    label: "AMA Memory Forget",
    description: "Clear all AMA memory for a user.",
    parameters: Type.Object({
      userId: Type.Optional(
        Type.String({
          description: "Optional AMA user id override.",
        }),
      ),
      confirm: Type.Boolean({
        description: "Must be true to clear all AMA memory.",
      }),
    }),
    async execute(_toolCallId, params) {
      const input = params as Record<string, unknown>;
      const userId = resolveUserId({
        userId: typeof input.userId === "string" ? input.userId : undefined,
      });
      if (input.confirm !== true) {
        return {
          content: [
            {
              type: "text",
              text: "AMA memory clear aborted because confirm was not true.",
            },
          ],
          details: {
            userId,
            cleared: false,
          },
        };
      }

      await ensureInitialized(userId);
      await deps.backend.clearAllMemory(userId);

      return {
        content: [
          {
            type: "text",
            text: `Cleared all AMA memory for ${userId}.`,
          },
        ],
        details: {
          userId,
          cleared: true,
        },
      };
    },
  };
}
