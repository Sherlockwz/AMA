// node_modules/.pnpm/openclaw@2026.7.1-2/node_modules/openclaw/dist/plugin-cache-primitives-BaxqicKH.js
var PluginLruCache = class {
  #defaultMaxEntries;
  #maxEntries;
  #entries = /* @__PURE__ */ new Map();
  constructor(defaultMaxEntries) {
    this.#defaultMaxEntries = normalizeMaxEntries(defaultMaxEntries, 1);
    this.#maxEntries = this.#defaultMaxEntries;
  }
  get maxEntries() {
    return this.#maxEntries;
  }
  get size() {
    return this.#entries.size;
  }
  setMaxEntriesForTest(value) {
    this.#maxEntries = typeof value === "number" ? normalizeMaxEntries(value, this.#defaultMaxEntries) : this.#defaultMaxEntries;
    this.#evictOldestEntries();
  }
  clear() {
    this.#entries.clear();
  }
  /** Returns a cached value and refreshes its recency when present. */
  get(cacheKey) {
    const cached = this.getResult(cacheKey);
    return cached.hit ? cached.value : void 0;
  }
  /** Returns a hit/miss result and promotes hits to the newest LRU position. */
  getResult(cacheKey) {
    if (!this.#entries.has(cacheKey)) return { hit: false };
    const cached = this.#entries.get(cacheKey);
    this.#entries.delete(cacheKey);
    this.#entries.set(cacheKey, cached);
    return {
      hit: true,
      value: cached
    };
  }
  /** Stores a value as the newest entry and evicts oldest entries past capacity. */
  set(cacheKey, value) {
    if (this.#entries.has(cacheKey)) this.#entries.delete(cacheKey);
    this.#entries.set(cacheKey, value);
    this.#evictOldestEntries();
  }
  #evictOldestEntries() {
    while (this.#entries.size > this.#maxEntries) {
      const oldestEntry = this.#entries.keys().next();
      if (oldestEntry.done) break;
      this.#entries.delete(oldestEntry.value);
    }
  }
};
function normalizeMaxEntries(value, fallback) {
  if (!Number.isFinite(value) || value <= 0) return fallback;
  return Math.max(1, Math.floor(value));
}

// node_modules/.pnpm/openclaw@2026.7.1-2/node_modules/openclaw/dist/ansi-D1GK_odF.js
var ESC_ANSI_CSI_PATTERN = "\\x1b\\[[\\x20-\\x3f]*[\\x40-\\x7e]";
var C1_ANSI_CSI_PATTERN = "\\x9b[\\x20-\\x3f]*[\\x40-\\x7e]";
var PARAMETERIZED_C1_ANSI_CSI_PATTERN = "\\x9b[\\x20-\\x3f]+[\\x40-\\x7e]";
var ANSI_CSI_PATTERN = `(?:${ESC_ANSI_CSI_PATTERN}|${C1_ANSI_CSI_PATTERN})`;
var ANSI_OSC_PATTERN = "(?:\\x1b\\]|\\x9d)[^\\x07\\x1b\\x9c]*(?:\\x1b\\\\|\\x07|\\x9c)";
var ANSI_CSI_REGEX = new RegExp(ANSI_CSI_PATTERN, "g");
var ANSI_OSC_REGEX = new RegExp(ANSI_OSC_PATTERN, "g");
var ANSI_SEQUENCE_REGEX = new RegExp(`${ANSI_OSC_PATTERN}|${ANSI_CSI_PATTERN}`, "g");
var SANITIZATION_ANSI_SEQUENCE_REGEX = new RegExp(`${ANSI_OSC_PATTERN}|${ESC_ANSI_CSI_PATTERN}|${PARAMETERIZED_C1_ANSI_CSI_PATTERN}`, "g");
var ANSI_COMPAT_SEQUENCE_REGEX = new RegExp(`(?:\\u001B\\][\\s\\S]*?(?:\\u0007|\\u001B\\u005C|\\u009C))|[\\u001B\\u009B][[\\]()#;?]*(?:\\d{1,4}(?:[;:]\\d{0,4})*)?[\\dA-PR-TZcf-nq-uy=><~]`, "g");
var graphemeSegmenter = typeof Intl !== "undefined" && "Segmenter" in Intl ? new Intl.Segmenter(void 0, { granularity: "grapheme" }) : null;

// node_modules/.pnpm/openclaw@2026.7.1-2/node_modules/openclaw/dist/json-schema-defaults-D-23eCDh.js
import { Compile } from "typebox/compile";

// node_modules/.pnpm/openclaw@2026.7.1-2/node_modules/openclaw/dist/schema-validator-BRkrm3P2.js
import { Compile as Compile2 } from "typebox/compile";
import { Format } from "typebox/format";
var schemaCache = new PluginLruCache(512);

// node_modules/.pnpm/openclaw@2026.7.1-2/node_modules/openclaw/dist/config-schema-ByzWLagI.js
function error(message) {
  return {
    success: false,
    error: { issues: [{
      path: [],
      message
    }] }
  };
}
function emptyPluginConfigSchema() {
  return {
    safeParse(value) {
      if (value === void 0) return {
        success: true,
        data: void 0
      };
      if (!value || typeof value !== "object" || Array.isArray(value)) return error("expected config object");
      if (Object.keys(value).length > 0) return error("config must be empty");
      return {
        success: true,
        data: value
      };
    },
    jsonSchema: {
      type: "object",
      additionalProperties: false,
      properties: {}
    }
  };
}

// node_modules/.pnpm/openclaw@2026.7.1-2/node_modules/openclaw/dist/plugin-entry-CM_XK0Yw.js
function createCachedLazyValueGetter(value, fallback) {
  let resolved = false;
  let cached;
  return () => {
    if (!resolved) {
      cached = (typeof value === "function" ? value() : value) ?? fallback;
      resolved = true;
    }
    return cached;
  };
}
function definePluginEntry({ id, name, description, kind, configSchema = emptyPluginConfigSchema, reload, nodeHostCommands, securityAuditCollectors, register }) {
  const getConfigSchema = createCachedLazyValueGetter(configSchema);
  return {
    id,
    name,
    description,
    ...kind ? { kind } : {},
    ...reload ? { reload } : {},
    ...nodeHostCommands ? { nodeHostCommands } : {},
    ...securityAuditCollectors ? { securityAuditCollectors } : {},
    get configSchema() {
      return getConfigSchema();
    },
    register
  };
}

// config.ts
import { userInfo } from "os";
var DEFAULTS = {
  llmApiKey: "",
  llmBaseUrl: "",
  embeddingApiUrl: "",
  modelMemory: "gpt-4o-mini",
  temperature: 0,
  memoryWindowSize: 1e5,
  memoryWindowLength: 20,
  turnRetrieve: 1,
  topK: 10,
  dataDir: "./ama-data",
  pythonExecutable: "",
  autoCapture: true,
  autoRecall: true,
  sidecarPort: 8321,
  sidecarAutoStart: false
};
var CONFIG_UI_HINTS = {
  llmApiKey: {
    label: "LLM API Key",
    sensitive: true,
    help: "Use ${AMA_LLM_API_KEY} or a SecretRef instead of storing plaintext."
  },
  llmBaseUrl: {
    label: "LLM Base URL",
    help: "OpenAI-compatible chat completions endpoint."
  },
  embeddingApiUrl: {
    label: "Embedding API URL",
    help: "Embedding endpoint used by AMA."
  },
  userId: {
    label: "Default User ID",
    placeholder: "default"
  },
  modelMemory: {
    label: "Memory Model",
    placeholder: "gpt-4o-mini"
  },
  temperature: {
    label: "Temperature",
    placeholder: "0.0"
  },
  memoryWindowSize: {
    label: "Window Token Limit",
    placeholder: "100000",
    advanced: true
  },
  memoryWindowLength: {
    label: "Window Item Limit",
    placeholder: "20",
    advanced: true
  },
  turnRetrieve: {
    label: "Max Retrieval Rounds",
    placeholder: "1",
    advanced: true
  },
  topK: {
    label: "Top K Results",
    placeholder: "10"
  },
  dataDir: {
    label: "Data Directory",
    placeholder: "./ama-data"
  },
  pythonExecutable: {
    label: "Python Executable",
    placeholder: ".venv/bin/python",
    advanced: true,
    help: "Optional Python path. AMA uses the repository .venv when available."
  },
  autoCapture: {
    label: "Auto-Capture"
  },
  autoRecall: {
    label: "Auto-Recall"
  },
  sidecarPort: {
    label: "Sidecar Port",
    placeholder: "8321",
    advanced: true
  },
  sidecarAutoStart: {
    label: "Auto-Start Sidecar",
    advanced: true
  }
};
var CONFIG_JSON_SCHEMA = {
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
    sidecarAutoStart: { type: "boolean" }
  },
  required: []
};
function defaultUserId() {
  try {
    return userInfo().username || "default";
  } catch {
    return "default";
  }
}
function resolveEnvString(value) {
  if (typeof value !== "string") return void 0;
  const trimmed = value.trim();
  const match = trimmed.match(/^\$\{([A-Z0-9_]+)\}$/);
  if (!match) return trimmed;
  return process.env[match[1]]?.trim() ?? "";
}
function readNumber(value, fallback) {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}
function readBoolean(value, fallback) {
  return typeof value === "boolean" ? value : fallback;
}
function parseAMAConfig(raw) {
  const cfg = raw && typeof raw === "object" && !Array.isArray(raw) ? raw : {};
  const llmApiKey = resolveEnvString(cfg.llmApiKey) ?? DEFAULTS.llmApiKey;
  const llmBaseUrl = resolveEnvString(cfg.llmBaseUrl) ?? DEFAULTS.llmBaseUrl;
  const embeddingApiUrl = resolveEnvString(cfg.embeddingApiUrl) ?? DEFAULTS.embeddingApiUrl;
  return {
    llmApiKey,
    llmBaseUrl,
    embeddingApiUrl,
    userId: resolveEnvString(cfg.userId) || defaultUserId(),
    modelMemory: resolveEnvString(cfg.modelMemory) ?? DEFAULTS.modelMemory,
    temperature: readNumber(cfg.temperature, DEFAULTS.temperature),
    memoryWindowSize: readNumber(
      cfg.memoryWindowSize,
      DEFAULTS.memoryWindowSize
    ),
    memoryWindowLength: readNumber(
      cfg.memoryWindowLength,
      DEFAULTS.memoryWindowLength
    ),
    turnRetrieve: readNumber(cfg.turnRetrieve, DEFAULTS.turnRetrieve),
    topK: readNumber(cfg.topK, DEFAULTS.topK),
    dataDir: resolveEnvString(cfg.dataDir) || DEFAULTS.dataDir,
    pythonExecutable: resolveEnvString(cfg.pythonExecutable) || DEFAULTS.pythonExecutable,
    autoCapture: readBoolean(cfg.autoCapture, DEFAULTS.autoCapture),
    autoRecall: readBoolean(cfg.autoRecall, DEFAULTS.autoRecall),
    sidecarPort: readNumber(cfg.sidecarPort, DEFAULTS.sidecarPort),
    sidecarAutoStart: readBoolean(
      cfg.sidecarAutoStart,
      DEFAULTS.sidecarAutoStart
    ),
    needsSetup: !llmApiKey || !llmBaseUrl || !embeddingApiUrl
  };
}

// backend/base.ts
var SidecarAPIError = class extends Error {
  constructor(status, path2, message) {
    super(`AMA sidecar error ${status} at ${path2}: ${message}`);
    this.status = status;
    this.path = path2;
    this.name = "SidecarAPIError";
  }
  status;
  path;
};

// backend/sidecar.ts
var SidecarBackend = class {
  baseUrl;
  constructor(port) {
    this.baseUrl = `http://127.0.0.1:${port}`;
  }
  async request(method, path2, body) {
    const response = await fetch(`${this.baseUrl}${path2}`, {
      method,
      headers: {
        "Content-Type": "application/json"
      },
      body: body === void 0 ? void 0 : JSON.stringify(body),
      signal: AbortSignal.timeout(3e4)
    });
    if (!response.ok) {
      let detail = response.statusText;
      try {
        const json = await response.json();
        detail = typeof json.detail === "string" ? json.detail : JSON.stringify(json);
      } catch {
      }
      throw new SidecarAPIError(response.status, path2, detail);
    }
    if (response.status === 204) {
      return {};
    }
    return await response.json();
  }
  async init(params) {
    await this.request("POST", "/init", params);
  }
  async forwardUser(params) {
    return this.request("POST", "/forward-user", params);
  }
  async forwardRobot(params) {
    return this.request("POST", "/forward-robot", params);
  }
  async forwardRetrieve(params) {
    return this.request("POST", "/forward-retrieve", params);
  }
  async judgeAndGenerate(user) {
    await this.request("POST", "/judge-and-generate", { user });
  }
  async clearAllMemory(user) {
    await this.request("POST", "/clear-all-memory", { user });
  }
  async health() {
    const result = await this.request(
      "GET",
      "/health"
    );
    return result.status === "ok";
  }
  async stats(user) {
    return this.request("GET", `/stats/${encodeURIComponent(user)}`);
  }
};

// tools/ama-process-turn.ts
import { Type } from "typebox";
function createAmaProcessTurnTool(deps) {
  const { ensureInitialized, resolveUserId, renderRetrievalPreview } = deps;
  return {
    name: "ama_process_turn",
    label: "AMA Process Turn",
    description: "Store and process a user turn through AMA's full memory pipeline.",
    parameters: Type.Object({
      message: Type.String({
        description: "User message content to process with AMA."
      }),
      userId: Type.Optional(
        Type.String({
          description: "Optional AMA user id override."
        })
      ),
      showUsage: Type.Optional(
        Type.Boolean({
          description: "Whether to request token usage logging from the sidecar."
        })
      )
    }),
    async execute(toolCallId, params, _signal, onUpdate) {
      const input = params;
      const message = typeof input.message === "string" ? input.message : "";
      const userId = resolveUserId({
        userId: typeof input.userId === "string" ? input.userId : void 0
      });
      const showUsage = input.showUsage === true;
      await ensureInitialized(userId);
      onUpdate?.({
        content: [
          {
            type: "text",
            text: `Processing AMA turn for ${userId}...`
          }
        ],
        details: {
          toolCallId,
          userId,
          stage: "started"
        }
      });
      const result = await deps.backend.forwardUser({
        user: userId,
        userInput: message,
        showUsage
      });
      const preview = renderRetrievalPreview(result.retrievals);
      return {
        content: [
          {
            type: "text",
            text: `AMA processed the turn for ${userId}.

Retrieval preview:
${preview}

Memory window items: ${result.memoryWindow.length}`
          }
        ],
        details: {
          toolCallId,
          userId,
          message,
          retrievals: result.retrievals,
          memoryWindow: result.memoryWindow
        }
      };
    }
  };
}

// tools/ama-retrieve.ts
import { Type as Type2 } from "typebox";
function createAmaRetrieveTool(deps) {
  const { ensureInitialized, resolveUserId, renderRetrievalPreview } = deps;
  return {
    name: "ama_retrieve",
    label: "AMA Retrieve",
    description: "Search AMA memory without mutating memory state.",
    parameters: Type2.Object({
      query: Type2.String({
        description: "Search query to send to AMA retrieval."
      }),
      userId: Type2.Optional(
        Type2.String({
          description: "Optional AMA user id override."
        })
      ),
      strongRetrieve: Type2.Optional(
        Type2.Boolean({
          description: "Enable stronger multi-channel retrieval."
        })
      ),
      showUsage: Type2.Optional(
        Type2.Boolean({
          description: "Whether to request token usage logging from the sidecar."
        })
      )
    }),
    async execute(_toolCallId, params) {
      const input = params;
      const query = typeof input.query === "string" ? input.query : "";
      const userId = resolveUserId({
        userId: typeof input.userId === "string" ? input.userId : void 0
      });
      const strongRetrieve = input.strongRetrieve === true;
      const showUsage = input.showUsage === true;
      await ensureInitialized(userId);
      const result = await deps.backend.forwardRetrieve({
        user: userId,
        userInput: query,
        strongRetrieve,
        showUsage
      });
      return {
        content: [
          {
            type: "text",
            text: `AMA retrieved memories for ${userId}.

` + renderRetrievalPreview(result.retrievals)
          }
        ],
        details: {
          userId,
          query,
          strongRetrieve,
          retrievals: result.retrievals,
          memoryWindow: result.memoryWindow
        }
      };
    }
  };
}

// tools/ama-process-assistant.ts
import { Type as Type3 } from "typebox";
function createAmaProcessAssistantTool(deps) {
  const { ensureInitialized, resolveUserId } = deps;
  return {
    name: "ama_process_assistant",
    label: "AMA Process Assistant",
    description: "Store an assistant reply into AMA without running retrieval.",
    parameters: Type3.Object({
      message: Type3.String({
        description: "Assistant message content to store in AMA."
      }),
      userId: Type3.Optional(
        Type3.String({
          description: "Optional AMA user id override."
        })
      ),
      timeInput: Type3.Optional(
        Type3.String({
          description: "Optional timestamp string for the assistant reply."
        })
      ),
      showUsage: Type3.Optional(
        Type3.Boolean({
          description: "Whether to request token usage logging from the sidecar."
        })
      )
    }),
    async execute(_toolCallId, params) {
      const input = params;
      const message = typeof input.message === "string" ? input.message : "";
      const userId = resolveUserId({
        userId: typeof input.userId === "string" ? input.userId : void 0
      });
      await ensureInitialized(userId);
      const result = await deps.backend.forwardRobot({
        user: userId,
        robotOutput: message,
        timeInput: typeof input.timeInput === "string" ? input.timeInput : void 0,
        showUsage: input.showUsage === true
      });
      return {
        content: [
          {
            type: "text",
            text: `AMA stored the assistant turn for ${userId}.

Memory window items: ${result.memoryWindow.length}`
          }
        ],
        details: {
          userId,
          message,
          memoryWindow: result.memoryWindow,
          constructDecision: result.constructDecision ?? null
        }
      };
    }
  };
}

// tools/ama-memory-list.ts
import { Type as Type4 } from "typebox";
function createAmaMemoryListTool(deps) {
  const { ensureInitialized, resolveUserId } = deps;
  return {
    name: "ama_memory_list",
    label: "AMA Memory List",
    description: "Show AMA memory statistics for a user.",
    parameters: Type4.Object({
      userId: Type4.Optional(
        Type4.String({
          description: "Optional AMA user id override."
        })
      )
    }),
    async execute(_toolCallId, params) {
      const input = params;
      const userId = resolveUserId({
        userId: typeof input.userId === "string" ? input.userId : void 0
      });
      await ensureInitialized(userId);
      const stats = await deps.backend.stats(userId);
      return {
        content: [
          {
            type: "text",
            text: `AMA stats for ${userId}:
- dialogue records: ${stats.records.dialogues}
- facts: ${stats.records.facts}
- episodes: ${stats.records.episodes}
- sentences: ${stats.records.sentences}
- memory window items: ${stats.memoryWindowSize}`
          }
        ],
        details: stats
      };
    }
  };
}

// tools/ama-memory-forget.ts
import { Type as Type5 } from "typebox";
function createAmaMemoryForgetTool(deps) {
  const { ensureInitialized, resolveUserId } = deps;
  return {
    name: "ama_memory_forget",
    label: "AMA Memory Forget",
    description: "Clear all AMA memory for a user.",
    parameters: Type5.Object({
      userId: Type5.Optional(
        Type5.String({
          description: "Optional AMA user id override."
        })
      ),
      confirm: Type5.Boolean({
        description: "Must be true to clear all AMA memory."
      })
    }),
    async execute(_toolCallId, params) {
      const input = params;
      const userId = resolveUserId({
        userId: typeof input.userId === "string" ? input.userId : void 0
      });
      if (input.confirm !== true) {
        return {
          content: [
            {
              type: "text",
              text: "AMA memory clear aborted because confirm was not true."
            }
          ],
          details: {
            userId,
            cleared: false
          }
        };
      }
      await ensureInitialized(userId);
      await deps.backend.clearAllMemory(userId);
      return {
        content: [
          {
            type: "text",
            text: `Cleared all AMA memory for ${userId}.`
          }
        ],
        details: {
          userId,
          cleared: true
        }
      };
    }
  };
}

// tools/ama-session-end.ts
import { Type as Type6 } from "typebox";
function createAmaSessionEndTool(deps) {
  const { ensureInitialized, resolveUserId } = deps;
  return {
    name: "ama_session_end",
    label: "AMA Session End",
    description: "Trigger AMA episodic synthesis for the current user.",
    parameters: Type6.Object({
      userId: Type6.Optional(
        Type6.String({
          description: "Optional AMA user id override."
        })
      )
    }),
    async execute(_toolCallId, params) {
      const input = params;
      const userId = resolveUserId({
        userId: typeof input.userId === "string" ? input.userId : void 0
      });
      await ensureInitialized(userId);
      await deps.backend.judgeAndGenerate(userId);
      return {
        content: [
          {
            type: "text",
            text: `AMA episodic generation completed for ${userId}.`
          }
        ],
        details: {
          userId,
          completed: true
        }
      };
    }
  };
}

// tools/index.ts
function collectPreviewLines(retrievals) {
  if (!retrievals) return [];
  if (Array.isArray(retrievals)) {
    return retrievals.slice(0, 5).map((item, index) => {
      const text = item && typeof item === "object" && "content" in item ? String(item.content ?? "") : String(item);
      return `${index + 1}. ${text}`;
    });
  }
  if (typeof retrievals === "object") {
    const record = retrievals;
    const lines = [];
    const sections = [
      ["Text", record.text_match_results],
      ["Facts", record.fact_match_results],
      ["Episodes", record.episodes_results]
    ];
    for (const [label, value] of sections) {
      if (!Array.isArray(value) || value.length === 0) continue;
      lines.push(`${label}:`);
      for (const [index, item] of value.slice(0, 3).entries()) {
        const text = item && typeof item === "object" && "content" in item ? String(item.content ?? "") : String(item);
        lines.push(`${index + 1}. ${text}`);
      }
    }
    return lines;
  }
  return [String(retrievals)];
}
function createInitParams(cfg, resolvePath, user) {
  return {
    user,
    dataDir: resolvePath(cfg.dataDir),
    modelMemory: cfg.modelMemory,
    temperature: cfg.temperature,
    memoryWindowSize: cfg.memoryWindowSize,
    memoryWindowLength: cfg.memoryWindowLength,
    turnRetrieve: cfg.turnRetrieve
  };
}
function registerAllTools(deps) {
  const tools = [
    createAmaProcessTurnTool(deps),
    createAmaProcessAssistantTool(deps),
    createAmaRetrieveTool(deps),
    createAmaMemoryListTool(deps),
    createAmaMemoryForgetTool(deps),
    createAmaSessionEndTool(deps)
  ];
  for (const tool of tools) {
    deps.api.registerTool(tool);
  }
}
function createRetrievalPreview(retrievals) {
  const lines = collectPreviewLines(retrievals);
  return lines.length > 0 ? lines.join("\n") : "No retrieval results.";
}

// recall.ts
function sanitizeQuery(input) {
  return input.replace(/\s+/g, " ").trim();
}
function formatSection(title, items) {
  if (items.length === 0) return "";
  const lines = items.map((item, index) => `${index + 1}. ${item.content ?? ""}`);
  return `${title}:
${lines.join("\n")}`;
}
function formatRetrievalsForInjection(retrievals) {
  if (Array.isArray(retrievals)) {
    const section = formatSection(
      "Retrieved Memories",
      retrievals.map((item) => ({ content: item.content }))
    );
    return section || "No AMA memories found.";
  }
  const sections = [
    formatSection(
      "Text Matches",
      (retrievals.text_match_results ?? []).map((item) => ({
        content: item.content
      }))
    ),
    formatSection(
      "Fact Matches",
      (retrievals.fact_match_results ?? []).map((item) => ({
        content: item.content
      }))
    ),
    formatSection(
      "Episodes",
      (retrievals.episodes_results ?? []).map((item) => ({
        content: item.content
      }))
    )
  ].filter(Boolean);
  return sections.length > 0 ? sections.join("\n\n") : "No AMA memories found.";
}
async function withTimeout(promise, timeoutMs) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      reject(new Error(`Timed out after ${timeoutMs}ms`));
    }, timeoutMs);
    promise.then(
      (value) => {
        clearTimeout(timer);
        resolve(value);
      },
      (error2) => {
        clearTimeout(timer);
        reject(error2);
      }
    );
  });
}
function registerRecallHook(params) {
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
            showUsage: false
          }),
          8e3
        );
        const injected = formatRetrievalsForInjection(result.retrievals);
        if (!injected || injected === "No AMA memories found.") {
          return;
        }
        return {
          prependContext: `<ama-memories>
${injected}
</ama-memories>`
        };
      } catch (error2) {
        api.logger.warn(`[ama] autoRecall skipped: ${String(error2)}`);
        return;
      }
    },
    { priority: 0 }
  );
}

// capture.ts
function flattenContent(content) {
  if (typeof content === "string") return content;
  if (Array.isArray(content)) {
    return content.map((item) => {
      if (!item || typeof item !== "object") return "";
      const record = item;
      if (typeof record.text === "string") return record.text;
      if (typeof record.thinking === "string") return "";
      return "";
    }).filter(Boolean).join("\n");
  }
  return "";
}
function extractMessages(messages) {
  return messages.map((message) => {
    if (!message || typeof message !== "object") return null;
    const record = message;
    const role = typeof record.role === "string" ? record.role : "";
    const text = flattenContent(record.content);
    if (!role || !text.trim()) return null;
    return { role, text: text.trim() };
  }).filter((item) => item !== null);
}
function registerCaptureHook(params) {
  const { api, backend, cfg, ensureInitialized, resolveUserId } = params;
  if (!cfg.autoCapture) {
    api.logger.info("[ama] autoCapture disabled; agent_end hook not registered");
    return;
  }
  api.on("agent_end", (event) => {
    void (async () => {
      const parsed = extractMessages(
        Array.isArray(event.messages) ? event.messages : []
      ).filter((message) => !message.text.includes("<ama-memories>"));
      const userMessage = [...parsed].reverse().find((message) => message.role === "user");
      const assistantMessage = [...parsed].reverse().find((message) => message.role === "assistant");
      if (!userMessage && !assistantMessage) return;
      const userId = resolveUserId();
      await ensureInitialized(userId);
      if (userMessage) {
        await backend.forwardUser({
          user: userId,
          userInput: userMessage.text,
          showUsage: false
        });
      }
      if (assistantMessage) {
        await backend.forwardRobot({
          user: userId,
          robotOutput: assistantMessage.text,
          showUsage: false
        });
      }
      await backend.judgeAndGenerate(userId);
    })().catch((error2) => {
      api.logger.warn(`[ama] autoCapture failed: ${String(error2)}`);
    });
  });
}

// service.ts
import { existsSync } from "fs";
import { spawn } from "child_process";
import path from "path";
function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
function registerSidecarService(params) {
  const { api, backend, cfg, ensureInitialized } = params;
  let child;
  api.registerService({
    id: "openclaw-ama-sidecar",
    start: async () => {
      if (!cfg.sidecarAutoStart) {
        api.logger.info("[ama] sidecarAutoStart disabled; service start skipped");
        return;
      }
      if (child && !child.killed) {
        return;
      }
      const pluginRoot = api.rootDir ?? process.cwd();
      const pythonDir = path.join(pluginRoot, "python");
      const venvPython = path.join(
        pluginRoot,
        ".venv",
        process.platform === "win32" ? "Scripts/python.exe" : "bin/python"
      );
      const pythonExecutable = cfg.pythonExecutable || (existsSync(venvPython) ? venvPython : "python3");
      child = spawn(
        pythonExecutable,
        ["-m", "uvicorn", "server:app", "--port", String(cfg.sidecarPort)],
        {
          cwd: pythonDir,
          env: {
            ...process.env,
            AMA_LLM_API_KEY: cfg.llmApiKey,
            AMA_LLM_BASE_URL: cfg.llmBaseUrl,
            AMA_EMBEDDING_URL: cfg.embeddingApiUrl
          }
        }
      );
      child.stdout.on("data", (chunk) => {
        api.logger.info(`[ama-sidecar] ${String(chunk).trim()}`);
      });
      child.stderr.on("data", (chunk) => {
        api.logger.warn(`[ama-sidecar] ${String(chunk).trim()}`);
      });
      child.on("exit", (code) => {
        api.logger.warn(`[ama-sidecar] exited with code ${String(code)}`);
        child = void 0;
      });
      for (let attempt = 0; attempt < 30; attempt += 1) {
        try {
          if (await backend.health()) {
            await ensureInitialized(cfg.userId);
            api.logger.info("[ama] sidecar service is ready");
            return;
          }
        } catch {
        }
        await sleep(500);
      }
      throw new Error("AMA sidecar did not become healthy in time");
    },
    stop: async () => {
      if (child && !child.killed) {
        child.kill("SIGTERM");
      }
      child = void 0;
    }
  });
}

// cli/commands.ts
function printSetupGuide(api) {
  api.logger.info(
    [
      "[ama] setup required",
      "Required environment variables:",
      "  AMA_LLM_API_KEY",
      "  AMA_LLM_BASE_URL",
      "  AMA_EMBEDDING_URL",
      "Example values for the OpenAI API:",
      "  AMA_LLM_BASE_URL=https://api.openai.com/v1/chat/completions",
      "  AMA_EMBEDDING_URL=https://api.openai.com/v1/embeddings",
      "Useful commands:",
      "  openclaw ama doctor",
      "  openclaw ama setup"
    ].join("\n")
  );
}
async function ensureReady(params) {
  const { api, cfg, backend, ensureInitialized, userId } = params;
  if (cfg.needsSetup) {
    printSetupGuide(api);
    return false;
  }
  await ensureInitialized(userId);
  try {
    const healthy = await backend.health();
    if (!healthy) {
      api.logger.warn("[ama] sidecar did not report healthy status");
    }
  } catch (error2) {
    api.logger.warn(`[ama] sidecar health check failed: ${String(error2)}`);
  }
  return true;
}
function registerCliCommands(params) {
  const { api, backend, cfg, ensureInitialized } = params;
  api.registerCli(({ program }) => {
    const ama = program.command("ama").description("AMA memory commands");
    ama.command("setup").description("Print AMA setup instructions").action(() => {
      printSetupGuide(api);
      api.logger.info(
        JSON.stringify(
          {
            openclawConfigPath: "~/.openclaw/openclaw.json",
            configTemplate: {
              plugins: {
                slots: {
                  memory: "openclaw-ama"
                },
                allow: ["openclaw-ama"],
                entries: {
                  "openclaw-ama": {
                    enabled: true,
                    hooks: {
                      allowConversationAccess: true
                    },
                    config: {
                      llmApiKey: "${AMA_LLM_API_KEY}",
                      llmBaseUrl: "${AMA_LLM_BASE_URL}",
                      embeddingApiUrl: "${AMA_EMBEDDING_URL}"
                    }
                  }
                }
              }
            }
          },
          null,
          2
        )
      );
    });
    ama.command("doctor").description("Check AMA configuration and sidecar connectivity").option("--user-id <userId>", "override AMA user id").action(async (options) => {
      const userId = options.userId ?? cfg.userId;
      const summary = {
        userId,
        configured: {
          llmApiKey: Boolean(cfg.llmApiKey),
          llmBaseUrl: Boolean(cfg.llmBaseUrl),
          embeddingApiUrl: Boolean(cfg.embeddingApiUrl)
        },
        values: {
          llmBaseUrl: cfg.llmBaseUrl || null,
          embeddingApiUrl: cfg.embeddingApiUrl || null,
          dataDir: cfg.dataDir,
          pythonExecutable: cfg.pythonExecutable || "auto",
          sidecarPort: cfg.sidecarPort,
          sidecarAutoStart: cfg.sidecarAutoStart,
          autoRecall: cfg.autoRecall,
          autoCapture: cfg.autoCapture,
          modelMemory: cfg.modelMemory
        }
      };
      api.logger.info(JSON.stringify(summary, null, 2));
      if (cfg.needsSetup) {
        printSetupGuide(api);
        return;
      }
      try {
        await ensureInitialized(userId);
        const healthy = await backend.health();
        api.logger.info(
          JSON.stringify(
            {
              sidecarHealthy: healthy
            },
            null,
            2
          )
        );
      } catch (error2) {
        api.logger.error(`[ama] doctor failed: ${String(error2)}`);
      }
    });
    ama.command("search").description("Search AMA memory").argument("<query>", "search query").option("--user-id <userId>", "override AMA user id").option("--strong", "enable strong retrieval").action(async (query, options) => {
      const userId = options.userId ?? cfg.userId;
      if (!await ensureReady({
        api,
        cfg,
        backend,
        ensureInitialized,
        userId
      })) {
        return;
      }
      const result = await backend.forwardRetrieve({
        user: userId,
        userInput: query,
        strongRetrieve: options.strong === true,
        showUsage: false
      });
      api.logger.info(JSON.stringify(result, null, 2));
    });
    ama.command("stats").description("Show AMA memory stats").option("--user-id <userId>", "override AMA user id").action(async (options) => {
      const userId = options.userId ?? cfg.userId;
      if (!await ensureReady({
        api,
        cfg,
        backend,
        ensureInitialized,
        userId
      })) {
        return;
      }
      const result = await backend.stats(userId);
      api.logger.info(JSON.stringify(result, null, 2));
    });
    ama.command("clear").description("Clear AMA memory").option("--user-id <userId>", "override AMA user id").action(async (options) => {
      const userId = options.userId ?? cfg.userId;
      if (!await ensureReady({
        api,
        cfg,
        backend,
        ensureInitialized,
        userId
      })) {
        return;
      }
      await backend.clearAllMemory(userId);
      api.logger.info(`Cleared AMA memory for ${userId}`);
    });
  }, { commands: ["ama"] });
}

// index.ts
var index_default = definePluginEntry({
  id: "openclaw-ama",
  name: "Memory (AMA)",
  description: "AMA adaptive memory for OpenClaw. Provides sidecar-backed retrieval and turn processing.",
  configSchema: {
    parse: parseAMAConfig,
    uiHints: CONFIG_UI_HINTS,
    jsonSchema: CONFIG_JSON_SCHEMA
  },
  register(api) {
    const cfg = parseAMAConfig(api.pluginConfig);
    const backend = new SidecarBackend(cfg.sidecarPort);
    const ensureInitialized = async (userId) => {
      await backend.init(
        createInitParams(
          cfg,
          (input) => api.resolvePath(input),
          userId ?? cfg.userId
        )
      );
    };
    registerCliCommands({
      api,
      backend,
      cfg,
      ensureInitialized
    });
    api.logger.info(
      cfg.needsSetup ? [
        "[ama] configuration incomplete; tools/hooks are not registered yet",
        "Required: AMA_LLM_API_KEY, AMA_LLM_BASE_URL, AMA_EMBEDDING_URL",
        "Example AMA_LLM_BASE_URL: https://api.openai.com/v1/chat/completions",
        "Example AMA_EMBEDDING_URL: https://api.openai.com/v1/embeddings",
        "Run `openclaw ama doctor` after configuring credentials."
      ].join("\n") : `[ama] sidecar backend configured on port ${cfg.sidecarPort}`
    );
    if (cfg.needsSetup) {
      return;
    }
    registerAllTools({
      api,
      backend,
      cfg,
      resolveUserId: (params) => params?.userId ?? cfg.userId,
      ensureInitialized,
      renderRetrievalPreview: createRetrievalPreview
    });
    registerRecallHook({
      api,
      backend,
      cfg,
      ensureInitialized,
      resolveUserId: (params) => params?.userId ?? cfg.userId
    });
    registerCaptureHook({
      api,
      backend,
      cfg,
      ensureInitialized,
      resolveUserId: (params) => params?.userId ?? cfg.userId
    });
    registerSidecarService({
      api,
      backend,
      cfg,
      ensureInitialized
    });
    void backend.health().catch((error2) => {
      api.logger.warn(`[ama] sidecar health check failed: ${String(error2)}`);
    });
  }
});
export {
  index_default as default
};
//# sourceMappingURL=index.js.map