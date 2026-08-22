import { Type } from "typebox";
import type { AnyAgentTool } from "openclaw/plugin-sdk";
import type { ToolDeps } from "./index.ts";

export function createAmaProcessTurnTool(deps: ToolDeps): AnyAgentTool {
  const { ensureInitialized, resolveUserId, renderRetrievalPreview } = deps;

  return {
    name: "ama_process_turn",
    label: "AMA Process Turn",
    description:
      "Store and process a user turn through AMA's full memory pipeline.",
    parameters: Type.Object({
      message: Type.String({
        description: "User message content to process with AMA.",
      }),
      userId: Type.Optional(
        Type.String({
          description: "Optional AMA user id override.",
        }),
      ),
      showUsage: Type.Optional(
        Type.Boolean({
          description: "Whether to request token usage logging from the sidecar.",
        }),
      ),
    }),
    async execute(toolCallId, params, _signal, onUpdate) {
      const input = params as Record<string, unknown>;
      const message = typeof input.message === "string" ? input.message : "";
      const userId = resolveUserId({
        userId: typeof input.userId === "string" ? input.userId : undefined,
      });
      const showUsage = input.showUsage === true;

      await ensureInitialized(userId);

      onUpdate?.({
        content: [
          {
            type: "text",
            text: `Processing AMA turn for ${userId}...`,
          },
        ],
        details: {
          toolCallId,
          userId,
          stage: "started",
        },
      });

      const result = await deps.backend.forwardUser({
        user: userId,
        userInput: message,
        showUsage,
      });

      const preview = renderRetrievalPreview(result.retrievals);
      return {
        content: [
          {
            type: "text",
            text:
              `AMA processed the turn for ${userId}.\n\n` +
              `Retrieval preview:\n${preview}\n\n` +
              `Memory window items: ${result.memoryWindow.length}`,
          },
        ],
        details: {
          toolCallId,
          userId,
          message,
          retrievals: result.retrievals,
          memoryWindow: result.memoryWindow,
        },
      };
    },
  };
}
