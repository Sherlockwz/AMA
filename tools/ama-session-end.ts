import { Type } from "typebox";
import type { AnyAgentTool } from "openclaw/plugin-sdk";
import type { ToolDeps } from "./index.ts";

export function createAmaSessionEndTool(deps: ToolDeps): AnyAgentTool {
  const { ensureInitialized, resolveUserId } = deps;

  return {
    name: "ama_session_end",
    label: "AMA Session End",
    description: "Trigger AMA episodic synthesis for the current user.",
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
      await deps.backend.judgeAndGenerate(userId);

      return {
        content: [
          {
            type: "text",
            text: `AMA episodic generation completed for ${userId}.`,
          },
        ],
        details: {
          userId,
          completed: true,
        },
      };
    },
  };
}
