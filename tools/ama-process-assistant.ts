import { Type } from "typebox";
import type { AnyAgentTool } from "openclaw/plugin-sdk";
import type { ToolDeps } from "./index.ts";

export function createAmaProcessAssistantTool(deps: ToolDeps): AnyAgentTool {
  const { ensureInitialized, resolveUserId } = deps;

  return {
    name: "ama_process_assistant",
    label: "AMA Process Assistant",
    description: "Store an assistant reply into AMA without running retrieval.",
    parameters: Type.Object({
      message: Type.String({
        description: "Assistant message content to store in AMA.",
      }),
      userId: Type.Optional(
        Type.String({
          description: "Optional AMA user id override.",
        }),
      ),
      timeInput: Type.Optional(
        Type.String({
          description: "Optional timestamp string for the assistant reply.",
        }),
      ),
      showUsage: Type.Optional(
        Type.Boolean({
          description: "Whether to request token usage logging from the sidecar.",
        }),
      ),
    }),
    async execute(_toolCallId, params) {
      const input = params as Record<string, unknown>;
      const message = typeof input.message === "string" ? input.message : "";
      const userId = resolveUserId({
        userId: typeof input.userId === "string" ? input.userId : undefined,
      });
      await ensureInitialized(userId);

      const result = await deps.backend.forwardRobot({
        user: userId,
        robotOutput: message,
        timeInput:
          typeof input.timeInput === "string" ? input.timeInput : undefined,
        showUsage: input.showUsage === true,
      });

      return {
        content: [
          {
            type: "text",
            text:
              `AMA stored the assistant turn for ${userId}.\n\n` +
              `Memory window items: ${result.memoryWindow.length}`,
          },
        ],
        details: {
          userId,
          message,
          memoryWindow: result.memoryWindow,
          constructDecision: result.constructDecision ?? null,
        },
      };
    },
  };
}
