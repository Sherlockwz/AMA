import type { AnyAgentTool, OpenClawPluginApi } from "openclaw/plugin-sdk";
import type { AMAConfig, InitParams } from "../types.ts";
import type { AMABackend } from "../backend/base.ts";
import { createAmaProcessTurnTool } from "./ama-process-turn.ts";
import { createAmaRetrieveTool } from "./ama-retrieve.ts";
import { createAmaProcessAssistantTool } from "./ama-process-assistant.ts";
import { createAmaMemoryListTool } from "./ama-memory-list.ts";
import { createAmaMemoryForgetTool } from "./ama-memory-forget.ts";
import { createAmaSessionEndTool } from "./ama-session-end.ts";

export interface ToolDeps {
  api: OpenClawPluginApi;
  backend: AMABackend;
  cfg: AMAConfig;
  resolveUserId: (params?: { userId?: string }) => string;
  ensureInitialized: (userId?: string) => Promise<void>;
  renderRetrievalPreview: (retrievals: unknown) => string;
}

function collectPreviewLines(retrievals: unknown): string[] {
  if (!retrievals) return [];
  if (Array.isArray(retrievals)) {
    return retrievals
      .slice(0, 5)
      .map((item, index) => {
        const text =
          item && typeof item === "object" && "content" in item
            ? String((item as Record<string, unknown>).content ?? "")
            : String(item);
        return `${index + 1}. ${text}`;
      });
  }
  if (typeof retrievals === "object") {
    const record = retrievals as Record<string, unknown>;
    const lines: string[] = [];
    const sections: Array<[string, unknown]> = [
      ["Text", record.text_match_results],
      ["Facts", record.fact_match_results],
      ["Episodes", record.episodes_results],
    ];
    for (const [label, value] of sections) {
      if (!Array.isArray(value) || value.length === 0) continue;
      lines.push(`${label}:`);
      for (const [index, item] of value.slice(0, 3).entries()) {
        const text =
          item && typeof item === "object" && "content" in item
            ? String((item as Record<string, unknown>).content ?? "")
            : String(item);
        lines.push(`${index + 1}. ${text}`);
      }
    }
    return lines;
  }
  return [String(retrievals)];
}

export function createInitParams(
  cfg: AMAConfig,
  resolvePath: (input: string) => string,
  user: string,
): InitParams {
  return {
    user,
    dataDir: resolvePath(cfg.dataDir),
    modelMemory: cfg.modelMemory,
    temperature: cfg.temperature,
    memoryWindowSize: cfg.memoryWindowSize,
    memoryWindowLength: cfg.memoryWindowLength,
    turnRetrieve: cfg.turnRetrieve,
  };
}

export function registerAllTools(deps: ToolDeps): void {
  const tools: AnyAgentTool[] = [
    createAmaProcessTurnTool(deps),
    createAmaProcessAssistantTool(deps),
    createAmaRetrieveTool(deps),
    createAmaMemoryListTool(deps),
    createAmaMemoryForgetTool(deps),
    createAmaSessionEndTool(deps),
  ];

  for (const tool of tools) {
    deps.api.registerTool(tool);
  }
}

export function createRetrievalPreview(retrievals: unknown): string {
  const lines = collectPreviewLines(retrievals);
  return lines.length > 0 ? lines.join("\n") : "No retrieval results.";
}
