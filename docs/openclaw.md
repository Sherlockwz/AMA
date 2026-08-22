# OpenClaw integration guide

The AMA plugin turns the research implementation into a local OpenClaw memory provider. It registers six agent tools, automatic recall/capture hooks, an `ama` CLI namespace, and a managed Python sidecar.

## 1. Prerequisites

- OpenClaw 2026.7.1-2 or a compatible newer version
- Node.js 22.22.3+ or 24.15+
- Python 3.10+
- pnpm 11+
- an OpenAI-compatible chat-completions endpoint
- an OpenAI-compatible embeddings endpoint returning 3,072-dimensional vectors

The current FAISS indices use dimension 3,072. When using OpenAI, select an embedding model/configuration that returns that size.

## 2. Install dependencies

```bash
git clone https://github.com/Sherlockwz/AMA.git
cd AMA
corepack enable pnpm
./scripts/setup.sh
```

During development, link the checkout:

```bash
openclaw plugins install --link .
openclaw plugins enable openclaw-ama
```

After the public repository is available, OpenClaw can also install directly from Git:

```bash
openclaw plugins install git:github.com/Sherlockwz/AMA@main
openclaw plugins enable openclaw-ama
```

Pin a release tag instead of `main` for production deployments.

## 3. Configure credentials

Export secrets in the environment that starts the OpenClaw gateway:

```bash
export AMA_LLM_API_KEY="your-api-key"
export AMA_LLM_BASE_URL="https://api.openai.com/v1/chat/completions"
export AMA_EMBEDDING_URL="https://api.openai.com/v1/embeddings"
```

Do not store a real key in the repository or paste it into an issue.

Add the plugin to `~/.openclaw/openclaw.json`:

```json5
{
  plugins: {
    slots: { memory: "openclaw-ama" },
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
          embeddingApiUrl: "${AMA_EMBEDDING_URL}",
          userId: "default",
          modelMemory: "gpt-4o-mini",
          dataDir: "./ama-data",
          turnRetrieve: 2,
          topK: 10,
          autoRecall: true,
          autoCapture: true,
          sidecarPort: 8321,
          sidecarAutoStart: true
        }
      }
    }
  }
}
```

`llmBaseUrl` must be the full chat-completions endpoint, not merely the API root. `embeddingApiUrl` must likewise be the full embeddings endpoint.

The separate `hooks.allowConversationAccess` permission allows AMA's `agent_end` hook to read the completed conversation turn for automatic capture. If you do not want this permission, omit it, set `autoCapture: false`, and write memories only through explicit AMA tools.

## 4. Verify

Restart the gateway, then run:

```bash
openclaw ama doctor
openclaw ama stats
openclaw ama search "What do you remember about me?"
```

For a simple end-to-end check:

1. Tell the agent a unique, non-sensitive fact such as “My demo project is named Juniper.”
2. Start a new session.
3. Ask “What is my demo project named?”
4. Run `openclaw ama stats` to inspect record counts.

## Configuration reference

| Option | Default | Purpose |
| --- | --- | --- |
| `llmApiKey` | empty | API key, preferably `${AMA_LLM_API_KEY}` |
| `llmBaseUrl` | empty | full OpenAI-compatible chat-completions URL |
| `embeddingApiUrl` | empty | full OpenAI-compatible embeddings URL |
| `userId` | OS username | logical memory namespace |
| `modelMemory` | `gpt-4o-mini` | model used by AMA's specialized agents |
| `temperature` | `0.0` | generation temperature |
| `memoryWindowSize` | `100000` | working-memory token limit |
| `memoryWindowLength` | `20` | target item count after window compaction |
| `turnRetrieve` | `1` | maximum retrieval feedback rounds |
| `topK` | `10` | retrieval result limit |
| `dataDir` | `./ama-data` | SQLite and FAISS persistence directory |
| `pythonExecutable` | automatic | optional explicit Python executable |
| `autoRecall` | `true` | inject relevant memories before prompt construction |
| `autoCapture` | `true` | capture the latest user and assistant turns after a run |
| `sidecarPort` | `8321` | local sidecar port |
| `sidecarAutoStart` | `false` | let OpenClaw start and stop the Python process |

## Registered tools

| Tool | Effect |
| --- | --- |
| `ama_process_turn` | retrieve, validate, refresh, and store a user turn |
| `ama_process_assistant` | store an assistant response |
| `ama_retrieve` | search memory without mutation |
| `ama_memory_list` | report window and persistent record counts |
| `ama_memory_forget` | delete all stored memory for a user |
| `ama_session_end` | trigger episodic synthesis |

The root [`SKILL.md`](../SKILL.md) gives an agent the operating policy for these tools. Installing the plugin provides the tools; the skill describes when and how an agent should use them.

## Manual sidecar mode

Set `sidecarAutoStart: false`, then run:

```bash
.venv/bin/python -m uvicorn python.server:app --host 127.0.0.1 --port 8321
```

Verify it independently:

```bash
curl http://127.0.0.1:8321/health
```

## Troubleshooting

### Configuration is incomplete

Run `openclaw ama setup`, verify all three `AMA_*` variables exist in the gateway process, and restart the gateway. The plugin deliberately does not register memory tools when credentials or endpoints are missing.

### Automatic recall works but automatic capture does not

Set `plugins.entries.openclaw-ama.hooks.allowConversationAccess` to `true` and restart the gateway. OpenClaw deliberately blocks conversation-reading hooks in third-party plugins until the operator grants this permission.

### The sidecar cannot start

Run `.venv/bin/python -m uvicorn python.server:app --port 8321` manually to expose the Python error. If the virtual environment is elsewhere, set `pythonExecutable` to its absolute path.

### Embedding or FAISS errors

Confirm the embedding endpoint returns vectors of dimension 3,072. Remove an incompatible test index only after backing up `dataDir`; deleting an index makes existing vector memory unavailable.

### Port 8321 is already in use

Choose another unused port and set the same value in the plugin configuration. The sidecar adapter always connects to `127.0.0.1`.

### `plugins validate` reports missing `defineToolPlugin` metadata

That authoring command validates simple tool-only plugins. AMA is a mixed plugin built with `definePluginEntry`; it also registers hooks, a service, and CLI commands. Validate it through an isolated install plus `openclaw plugins inspect openclaw-ama --runtime` and `openclaw plugins doctor`.
