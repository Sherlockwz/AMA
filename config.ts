import { userInfo } from "node:os";
import type { AMAConfig } from "./types.ts";

const DEFAULTS = {
  llmApiKey: "",
  llmBaseUrl: "",
  embeddingApiUrl: "",
  modelMemory: "gpt-4o-mini",
  temperature: 0.0,
  memoryWindowSize: 100000,
  memoryWindowLength: 20,
  turnRetrieve: 1,
  topK: 10,
  dataDir: "./ama-data",
  pythonExecutable: "",
  autoCapture: true,
  autoRecall: true,
  sidecarPort: 8321,
  sidecarAutoStart: false,
} as const;

export const CONFIG_UI_HINTS = {
  llmApiKey: {
    label: "LLM API Key",
    sensitive: true,
    help: "Use ${AMA_LLM_API_KEY} or a SecretRef instead of storing plaintext.",
  },
  llmBaseUrl: {
    label: "LLM Base URL",
    help: "OpenAI-compatible chat completions endpoint.",
  },
  embeddingApiUrl: {
    label: "Embedding API URL",
    help: "Embedding endpoint used by AMA.",
  },
  userId: {
    label: "Default User ID",
    placeholder: "default",
  },
  modelMemory: {
    label: "Memory Model",
    placeholder: "gpt-4o-mini",
  },
  temperature: {
    label: "Temperature",
    placeholder: "0.0",
  },
  memoryWindowSize: {
    label: "Window Token Limit",
    placeholder: "100000",
    advanced: true,
  },
  memoryWindowLength: {
    label: "Window Item Limit",
    placeholder: "20",
    advanced: true,
  },
  turnRetrieve: {
    label: "Max Retrieval Rounds",
    placeholder: "1",
    advanced: true,
  },
  topK: {
    label: "Top K Results",
    placeholder: "10",
  },
  dataDir: {
    label: "Data Directory",
    placeholder: "./ama-data",
  },
  pythonExecutable: {
    label: "Python Executable",
    placeholder: ".venv/bin/python",
    advanced: true,
    help: "Optional Python path. AMA uses the repository .venv when available.",
  },
  autoCapture: {
    label: "Auto-Capture",
  },
  autoRecall: {
    label: "Auto-Recall",
  },
  sidecarPort: {
    label: "Sidecar Port",
    placeholder: "8321",
    advanced: true,
  },
  sidecarAutoStart: {
    label: "Auto-Start Sidecar",
    advanced: true,
  },
} as const;

export const CONFIG_JSON_SCHEMA = {
  type: "object",
  additionalProperties: false,
  properties: {
    llmApiKey: { type: "string" },
    llmBaseUrl: { type: "string" },
    embeddingApiUrl: { type: "string" },
    userId: { type: "string" },
    modelMemory: { type: "string" },
    temperature: { type: "number" },
    memoryWindowSize: { type: "number" },
    memoryWindowLength: { type: "number" },
    turnRetrieve: { type: "number" },
    topK: { type: "number" },
    dataDir: { type: "string" },
    pythonExecutable: { type: "string" },
    autoCapture: { type: "boolean" },
    autoRecall: { type: "boolean" },
    sidecarPort: { type: "number" },
    sidecarAutoStart: { type: "boolean" },
  },
  required: [],
} as const;

function defaultUserId(): string {
  try {
    return userInfo().username || "default";
  } catch {
    return "default";
  }
}

function resolveEnvString(value: unknown): string | undefined {
  if (typeof value !== "string") return undefined;
  const trimmed = value.trim();
  const match = trimmed.match(/^\$\{([A-Z0-9_]+)\}$/);
  if (!match) return trimmed;
  return process.env[match[1]]?.trim() ?? "";
}

function readNumber(value: unknown, fallback: number): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function readBoolean(value: unknown, fallback: boolean): boolean {
  return typeof value === "boolean" ? value : fallback;
}

export function parseAMAConfig(raw: unknown): AMAConfig {
  const cfg =
    raw && typeof raw === "object" && !Array.isArray(raw)
      ? (raw as Record<string, unknown>)
      : {};

  const llmApiKey = resolveEnvString(cfg.llmApiKey) ?? DEFAULTS.llmApiKey;
  const llmBaseUrl = resolveEnvString(cfg.llmBaseUrl) ?? DEFAULTS.llmBaseUrl;
  const embeddingApiUrl =
    resolveEnvString(cfg.embeddingApiUrl) ?? DEFAULTS.embeddingApiUrl;

  return {
    llmApiKey,
    llmBaseUrl,
    embeddingApiUrl,
    userId: resolveEnvString(cfg.userId) || defaultUserId(),
    modelMemory:
      resolveEnvString(cfg.modelMemory) ?? DEFAULTS.modelMemory,
    temperature: readNumber(cfg.temperature, DEFAULTS.temperature),
    memoryWindowSize: readNumber(
      cfg.memoryWindowSize,
      DEFAULTS.memoryWindowSize,
    ),
    memoryWindowLength: readNumber(
      cfg.memoryWindowLength,
      DEFAULTS.memoryWindowLength,
    ),
    turnRetrieve: readNumber(cfg.turnRetrieve, DEFAULTS.turnRetrieve),
    topK: readNumber(cfg.topK, DEFAULTS.topK),
    dataDir: resolveEnvString(cfg.dataDir) || DEFAULTS.dataDir,
    pythonExecutable:
      resolveEnvString(cfg.pythonExecutable) || DEFAULTS.pythonExecutable,
    autoCapture: readBoolean(cfg.autoCapture, DEFAULTS.autoCapture),
    autoRecall: readBoolean(cfg.autoRecall, DEFAULTS.autoRecall),
    sidecarPort: readNumber(cfg.sidecarPort, DEFAULTS.sidecarPort),
    sidecarAutoStart: readBoolean(
      cfg.sidecarAutoStart,
      DEFAULTS.sidecarAutoStart,
    ),
    needsSetup: !llmApiKey || !llmBaseUrl || !embeddingApiUrl,
  };
}
