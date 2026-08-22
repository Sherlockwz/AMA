import { Type } from "typebox";
import type { AnyAgentTool } from "openclaw/plugin-sdk";
import type { ToolDeps } from "./index.ts";

export function createAmaRetrieveTool(deps: ToolDeps): AnyAgentTool {
  const { ensureInitialized, resolveUserId, renderRetrievalPreview } = deps;

  return {
    name: "ama_retrieve",
    label: "AMA Retrieve",
    description: "Search AMA memory without mutating memory state.",
    parameters: Type.Object({
      query: Type.String({
        description: "Search query to send to AMA retrieval.",
      }),
      userId: Type.Optional(
        Type.String({
          description: "Optional AMA user id override.",
        }),
      ),
      strongRetrieve: Type.Optional(
        Type.Boolean({
          description: "Enable stronger multi-channel retrieval.",
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
      const query = typeof input.query === "string" ? input.query : "";
      const userId = resolveUserId({
        userId: typeof input.userId === "string" ? input.userId : undefined,
      });
      const strongRetrieve = input.strongRetrieve === true;
      const showUsage = input.showUsage === true;

      await ensureInitialized(userId);

      const result = await deps.backend.forwardRetrieve({
        user: userId,
        userInput: query,
        strongRetrieve,
        showUsage,
      });

      return {
        content: [
          {
            type: "text",
            text:
              `AMA retrieved memories for ${userId}.\n\n` +
              renderRetrievalPreview(result.retrievals),
          },
        ],
        details: {
          userId,
          query,
          strongRetrieve,
          retrievals: result.retrievals,
          memoryWindow: result.memoryWindow,
        },
      };
    },
  };
}
