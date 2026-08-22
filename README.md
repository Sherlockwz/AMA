# AMA: Adaptive Memory via Multi-Agent Collaboration

<p align="center">
  <a href="https://aclanthology.org/2026.findings-acl.152/"><img src="https://img.shields.io/badge/Paper-Findings%20of%20ACL%202026-4b5563" alt="ACL paper"></a>
  <a href="https://arxiv.org/abs/2601.20352"><img src="https://img.shields.io/badge/arXiv-2601.20352-b31b1b" alt="arXiv"></a>
  <a href="https://huggingface.co/papers/2601.20352"><img src="https://img.shields.io/badge/🤗%20Daily%20Paper-Hugging%20Face-ffcc4d" alt="Hugging Face paper"></a>
  <a href="https://sherlockwz.github.io/AMA/"><img src="https://img.shields.io/badge/Project%20Page-AMA-2563eb" alt="Project page"></a>
  <a href="https://github.com/Sherlockwz/AMA/actions/workflows/ci.yml"><img src="https://github.com/Sherlockwz/AMA/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-Apache--2.0-green" alt="Apache-2.0 license"></a>
</p>

<p align="center">
  Official research implementation and OpenClaw memory plugin for <strong>AMA</strong>.
</p>

<p align="center">
  <a href="README_zh-CN.md">中文说明</a> ·
  <a href="docs/reproduction.md">Reproduction</a> ·
  <a href="docs/openclaw.md">OpenClaw setup</a> ·
  <a href="docs/architecture.md">Architecture</a>
</p>

AMA is a long-term memory framework for LLM agents. It coordinates four specialized agents—**Constructor**, **Retriever**, **Judge**, and **Refresher**—to build multi-granular memories, route each query to the appropriate granularity, verify retrieved evidence, and keep evolving knowledge consistent.

This repository contains:

- the research implementation used to study AMA;
- an OpenAI-compatible Python sidecar backed by SQLite and FAISS;
- an OpenClaw memory plugin with automatic recall and capture;
- reproducibility, architecture, and deployment documentation.

## Overview

![AMA framework](docs/assets/ama-framework.png)

| Agent | Responsibility |
| --- | --- |
| Constructor | Builds raw-text, fact-knowledge, and episodic memories. |
| Retriever | Rewrites queries and adaptively routes them to the best memory granularity. |
| Judge | Checks relevance and logical consistency, requesting another retrieval round when needed. |
| Refresher | Updates or removes conflicting memories to preserve temporal consistency. |

With GPT-4o-mini on LoCoMo, AMA reaches an overall LLM score of **0.774**. At the default retrieval depth \(K_r=2\), it processes **3,613 tokens**—about **19%** of the 18,625-token FullContext input—and records **3.91 s** latency versus **7.21 s** for FullContext. On LongMemEval\(_s\), AMA reaches **0.698** average accuracy and **0.897** on knowledge-update questions.

## Installation

### Requirements

- Python 3.10+
- Node.js 22.22.3+ (Node.js 24.15+ is also supported)
- pnpm 11+
- an OpenAI-compatible chat-completions endpoint and embedding endpoint

### Set up the repository

```bash
git clone https://github.com/Sherlockwz/AMA.git
cd AMA
corepack enable pnpm
./scripts/setup.sh
```

Configure credentials in your shell. Do not commit API keys.

```bash
export AMA_LLM_API_KEY="your-api-key"
export AMA_LLM_BASE_URL="https://api.openai.com/v1/chat/completions"
export AMA_EMBEDDING_URL="https://api.openai.com/v1/embeddings"
```

The implementation accepts any provider exposing compatible chat-completions and embeddings APIs. Copy [`.env.example`](.env.example) when you need a local template.

## OpenClaw plugin

Install the local checkout during development:

```bash
openclaw plugins install --link .
openclaw plugins enable openclaw-ama
```

Then add the following to `~/.openclaw/openclaw.json`:

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
          dataDir: "./ama-data",
          sidecarAutoStart: true,
          autoRecall: true,
          autoCapture: true
        }
      }
    }
  }
}
```

`allowConversationAccess` is OpenClaw's explicit permission for the `agent_end` hook to read the completed turn. It is required for `autoCapture`; omit it and set `autoCapture: false` if you only want explicit tool-based writes.

Restart the OpenClaw gateway and verify the integration:

```bash
openclaw ama doctor
openclaw ama stats
openclaw ama search "What do you remember about me?"
```

See the complete [OpenClaw setup guide](docs/openclaw.md) for Git installation, manual sidecar startup, configuration options, tools, and troubleshooting.

## Research code

The original Python implementation lives in [`python/AdaptiveMemory`](python/AdaptiveMemory). For a direct sidecar smoke test:

```bash
.venv/bin/python -m uvicorn python.server:app --host 127.0.0.1 --port 8321
curl http://127.0.0.1:8321/health
```

Evaluation entry points are in [`python/AdaptiveMemory/Core`](python/AdaptiveMemory/Core). Benchmark datasets are not redistributed in this repository; follow [the reproduction guide](docs/reproduction.md) to obtain and place them.

## Repository structure

```text
AMA/
├── python/AdaptiveMemory/   # research implementation
├── python/server.py         # local HTTP sidecar
├── backend/                 # OpenClaw ↔ sidecar adapter
├── tools/                   # six agent-callable AMA tools
├── docs/                    # guides, project page, and paper figures
├── tests/                   # TypeScript and Python unit tests
├── index.ts                 # OpenClaw plugin entry
├── openclaw.plugin.json     # plugin manifest
└── SKILL.md                 # agent-facing operating instructions
```

## Validation

```bash
./scripts/check.sh
```

This runs strict TypeScript checks, Vitest, Python unit tests, Python bytecode compilation, and the production bundle.

## Citation

If AMA helps your work, please cite:

```bibtex
@inproceedings{huang-etal-2026-ama,
  title     = {{AMA}: Adaptive Memory via Multi-Agent Collaboration},
  author    = {Huang, Weiquan and Wang, Zixuan and Lin, Hehai and Wang, Sudong and Xu, Bo and Li, Qian and Zhu, Beier and Yang, Linyi and Qin, Chengwei},
  booktitle = {Findings of the Association for Computational Linguistics: ACL 2026},
  year      = {2026},
  pages     = {3099--3120},
  doi       = {10.18653/v1/2026.findings-acl.152},
  url       = {https://aclanthology.org/2026.findings-acl.152/}
}
```

Machine-readable citation files are available as [`CITATION.cff`](CITATION.cff) and [`CITATION.bib`](CITATION.bib).

## Contributing

Bug reports, reproducibility notes, documentation improvements, and integrations are welcome. Please read [`CONTRIBUTING.md`](CONTRIBUTING.md) and use the issue templates.

## License

Released under the [Apache License 2.0](LICENSE).
