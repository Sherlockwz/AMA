# AMA：通过多智能体协作实现自适应记忆

<p align="center">
  <a href="https://aclanthology.org/2026.findings-acl.152/">ACL 2026 论文</a> ·
  <a href="https://arxiv.org/abs/2601.20352">arXiv</a> ·
  <a href="https://sherlockwz.github.io/AMA/">项目主页</a> ·
  <a href="README.md">English</a>
</p>

AMA（Adaptive Memory via Multi-Agent Collaboration）是一个面向 LLM Agent 长期交互的记忆框架。它通过 **Constructor、Retriever、Judge、Refresher** 四个专门智能体协同管理记忆的构建、检索、验证和更新，并使用原始文本、事实知识与情景记忆三种粒度满足不同推理需求。

![AMA 框架](docs/assets/ama-framework.png)

本仓库同时提供论文研究实现、基于 SQLite/FAISS 的 Python sidecar，以及可直接接入 OpenClaw 的记忆插件。

## 快速开始

需要 Python 3.10+、Node.js 22.22.3+（也支持 24.15+）和 pnpm 11+。

```bash
git clone https://github.com/Sherlockwz/AMA.git
cd AMA
corepack enable pnpm
./scripts/setup.sh

export AMA_LLM_API_KEY="your-api-key"
export AMA_LLM_BASE_URL="https://api.openai.com/v1/chat/completions"
export AMA_EMBEDDING_URL="https://api.openai.com/v1/embeddings"
```

安装 OpenClaw 插件：

```bash
openclaw plugins install --link .
openclaw plugins enable openclaw-ama
```

完整的 OpenClaw 配置、工具列表和排错方法见 [`docs/openclaw.md`](docs/openclaw.md)，论文实验复现说明见 [`docs/reproduction.md`](docs/reproduction.md)。

## 论文结果

- LoCoMo（GPT-4o-mini）整体 LLM Score：**0.774**。
- 默认 \(K_r=2\) 时使用 **3,613 tokens**，约为 FullContext 的 **19%**。
- LongMemEval\(_s\) 平均准确率：**0.698**；知识更新任务：**0.897**。

## 引用

```bibtex
@inproceedings{huang-etal-2026-ama,
  title     = {{AMA}: Adaptive Memory via Multi-Agent Collaboration},
  author    = {Huang, Weiquan and Wang, Zixuan and Lin, Hehai and Wang, Sudong and Xu, Bo and Li, Qian and Zhu, Beier and Yang, Linyi and Qin, Chengwei},
  booktitle = {Findings of the Association for Computational Linguistics: ACL 2026},
  year      = {2026},
  pages     = {3099--3120},
  doi       = {10.18653/v1/2026.findings-acl.152}
}
```

本项目使用 [Apache-2.0](LICENSE) 许可证。
