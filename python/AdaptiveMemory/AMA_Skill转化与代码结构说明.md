# AMA（Automatic Memory Agent）Skill 转化与代码结构说明

本文档用于配合将 AMA 研究接入 OpenClaw 等 Agent 工具链（参考 [ClawHub 上 mem0 的 OpenClaw skill 形态](https://clawhub.ai/xray2016/openclaw-mem0)），向合作方说明**开发思路概要**以及**当前仓库内原始代码的目录结构与各文件职责**。

---

## 一、开发思路（面向 OpenClaw / Skill 化）

1. **能力边界对齐**  
   AMA 的核心是对话记忆的全流程：**检索策略选择 → 向量检索 → 充分性/冲突判断 → 必要时刷新（更新/删除元信息）→ 事实抽取与写入 → 可选的篇章级 episodic 摘要**。Skill 化时，需要把这些阶段映射为 Agent 可调用的**明确接口**（例如：写入一轮对话、检索上下文、清空会话窗口等），而不是仅暴露一个黑盒脚本。

2. **与 mem0 skill 的对照**  
   mem0 将「记忆服务」封装为可安装能力；AMA 侧可同样提供：初始化用户/任务命名空间、追加记忆、查询记忆、（可选）重置记忆等命令或工具描述，并在 Skill 元数据中声明依赖（LLM API、Embedding API、本地 `Store/` 持久化路径）。

3. **配置与密钥**  
   当前代码通过 `Settings/config.py` 配置 `api_key`、`base_url`、`embedding_url`。Skill 安装后应改为**环境变量或 OpenClaw 密钥管理**，避免把密钥写进仓库。

4. **持久化路径**  
   运行时会在项目工作目录下创建 `Store/AMA.db` 以及 `Store/{user}_{text|fact|sentence}_Index.faiss`。Skill 需约定**可写的统一数据目录**（例如用户主目录下的子文件夹），避免与多用户或多任务冲突。

5. **评测代码与线上 Skill 分离**  
   `Core/eval*.py` 与 `Core/eval.py` 面向 LoCoMo 等 benchmark，用于论文级对比；接入 GUI Agent 或小艺联调时，**优先复用 `Core/AMA.py` 的 `forward*` 管线**，评测脚本可作为「效果验证」保留在仓库，不必全部打进最小 Skill 包。

6. **后续与 GUI Agent 结合**  
   将小艺 GUI Agent 的「用户操作/界面状态」编码为与 LoCoMo 类似的结构化输入（例如 JSON：`speaker` / `text` / 可选图像字段），即可复用 `forwardUser` 的事实抽取与存储逻辑；检索侧可用 `forwardRetrieve` 或封装后的轻量 API 注入系统提示或工具结果。

---

## 二、目录结构总览

以下树形结构反映 **`AdaptiveMemory` 包内** Python 源码的组织方式（不含运行生成的 `Store/` 内数据库与 FAISS 文件）。

```text
AdaptiveMemory/
├── Core/
│   ├── AMA.py              # AMA 主类：记忆管线、检索、刷新、写入、短期窗口
│   ├── eval.py             # LoCoMo 评测指标（F1、BLEU、LLM Judge）与结果合并示例
│   ├── evalProcess.py      # LoCoMo：对话入库管线（按 session 调用 forwardUser）
│   └── evalLocomo.py       # LoCoMo：问答评测（forwardRetrieve + chatAgent 写结果 JSON）
├── Model/
│   └── model.py            # memoryAgent（LLM 调用与各阶段推理）与 chatAgent（QA）
├── Settings/
│   ├── config.py           # API Key、Chat Completions URL、Embedding URL
│   └── prompt.py           # 检索 / 判断 / 构造 / 刷新 / QA / 篇章等英文 Prompt 模板
└── StoreFunc/
    ├── Faiss/
    │   ├── embedding.py    # 调用 Embedding API（单条与批量）
    │   └── faissFunc.py    # FAISS 索引：创建、增删、检索；text / fact / sentence 三类
    └── SQLite/
        └── sqliteFunc.py   # SQLite：表结构、增删改查、按 id / dia_id 查询等
```

运行后常见**生成物**（不在上述源码树中，但需知情）：

- `Store/AMA.db`：SQLite 数据库。  
- `Store/{user}_text_Index.faiss`、`Store/{user}_fact_Index.faiss`、`Store/{user}_sentence_Index.faiss`：与向量通道对应的 FAISS 索引文件。

---

## 三、主要文件列表与职责说明

### 1. `Core/AMA.py`

- **定位**：AMA 的**主入口类** `AMA`，串联记忆管理的完整业务逻辑。  
- **主要职责**：  
  - **初始化**：按 `user` 创建/连接 SQLite 表（用户主表、`{user}Fact`、`{user}Episode`、`{user}Sentence`），并创建/加载 FAISS 索引（text、fact；sentence 在 episodic 写入时使用）。  
  - **短期记忆窗口**：`memoryWindow`（`deque`）、`adjustMemoryWindow` / `countMemoryTokens` 基于条数与 token 上限收缩窗口。  
  - **检索**：`retrieve` / `retrieveSingleChannel` / `retrieveDualChannel`，操作符对应事实通道、原文通道、双通道；内部调用 `faissFunc` + `sqliteFunc`。  
  - **刷新**：`refresh`（更新 operator 4、删除 operator 5）及 `refreshUpdate` / `refreshDelete`，在冲突等情形下更新相关行的 `meta` 等。  
  - **写入**：`constructFullWrite`（主表 + text 向量）、`constructFactWrite`（事实表 + fact 向量）、`constructEpisodicWrite`（episode + 分句表 + sentence 向量）。  
  - **端到端前向**：`forwardUser`（用户轮：检索 → Judge → 可选 Refresh → 并行「篇章边界判断 + 事实构造写入」→ 更新窗口）；`forwardRobot`（助手轮：侧重构造写入）；`forwardRetrieve`（问答/取上下文）；`judgeAndGenerate`（会话结束补 episodic）。  
- **辅助**：`split_sentences` 用于将 episode 正文拆句并写入 sentence 级索引。

### 2. `Model/model.py`

- **定位**：与大模型 API 交互的薄封装。  
- **`memoryAgent`**：  
  - `inference`：通用 Chat Completions 请求（`requests` + `Settings.config` 的 `api_key` / `base_url`）。  
  - `inferenceRetrieve` / `inferenceJudge` / `inferenceRefresh` / `inferenceConstruct` / `inferenceJudgeEpisode` / `inferenceGenerateEpisode`：分别填充 `prompt.py` 中对应模板并解析 JSON，为 `AMA` 各阶段提供结构化决策。  
- **`chatAgent`**：使用 `QANemoriPrompt` 等模板，在给定 `memoryInfo` 下做**阅读理解式问答**（LoCoMo 评测答案生成用）。

### 3. `Settings/config.py`

- **定位**：**敏感配置与端点**。  
- **内容**：`api_key`、`base_url`（聊天补全）、`embedding_url`（向量）。部署或 Skill 化时应改为环境变量注入，仓库内勿提交真实密钥。

### 4. `Settings/prompt.py`

- **定位**：**全部阶段提示词模板**（英文）。  
- **主要变量/模板**：  
  - `retrievePromptEN`：根据记忆窗口与用户输入选择检索操作符（1/2/3）与 `retrieveQuery`、`topK`。  
  - `judgePromptEN`：判断检索结果是否足够、是否冲突（如 -1 通过、9 再检索、-2 冲突）。  
  - `refreshPromptEN`：事实刷新（不操作 / 更新 / 删除）。  
  - `constructPromptEN_FTF`：事实抽取与时间戳规则（严格显式时间）。  
  - `qaPromptEN`、`QANemoriPrompt`：问答风格与证据字段（供评测或对话 QA）。  
  - `judgeEpisodePromptEN`、`generateEpisodePrompt`：篇章边界检测与 episodic 叙事生成。

### 5. `StoreFunc/SQLite/sqliteFunc.py`

- **定位**：**持久化关系数据**层，数据库文件为 `Store/AMA.db`。  
- **主要职责**：  
  - 建库、按用户/类型建表：`createTable`、`createFactKnowledgeTable`、`createTableEpisode`、`createSentenceTable`。  
  - 插入与批量插入：`insertRecord`、`insertFactRecord`、`insertRecordEpisode`、`insertBatchRecords` 等。  
  - 查询：`queryById`、`queryByIdList`（保持 id 顺序）、`queryLastRecord`、`queryByDiaId`。  
  - 更新与元信息追加：`updateRecord`、`updateMetaOnly`、`updateFactRecords`。  
  - 删除：`deleteRecordsByIdList`、`deleteTable`、`deleteUser` / `deleteAllUsers` 等。

### 6. `StoreFunc/Faiss/embedding.py`

- **定位**：**向量嵌入** HTTP 调用。  
- **职责**：`getEmbedding`（单条）、`getEmbeddingsList`（批量），默认模型与 `config.embedding_url` 配套；返回浮点向量供 FAISS 使用。

### 7. `StoreFunc/Faiss/faissFunc.py`

- **定位**：**向量索引**（FAISS `IndexFlatIP` + `IndexIDMap`，L2 归一化后内积等价余弦相关场景）。  
- **主要职责**：  
  - `loadFaissIndex` / `makeTwoTypesIndex`：按用户加载或新建 text、fact 索引文件。  
  - `addToFaissIndex`、`addBatchToFaissIndex`、`addBatchToSentencesIndex`：写入向量并与 SQLite 自增 id 对齐。  
  - `searchFaissIndex`：按 `embedType`（`text` / `fact` / `sentence`）检索 topK。  
  - `deleteFromFaissIndex`、`deleteUserFaissIndices`：删除向量或整个用户的索引文件。

### 8. `Core/evalProcess.py`

- **定位**：**LoCoMo 数据预处理与记忆构建**脚本。  
- **流程**：读取 `locomo10.json` 中某一 `user_id` 对应人物的 `conversation`，按 `session_k` 循环，将每轮转为字典后调用 `AMA.forwardUser`，session 结束后调用 `judgeAndGenerate`。  
- **入口**：命令行 `--user_id`。

### 9. `Core/evalLocomo.py`

- **定位**：**LoCoMo 问答评测**脚本。  
- **流程**：同一 `user_id` 下读取 `qa` 列表，跳过 category 5；`forwardRetrieve` 取记忆上下文，`chatAgent.chat` 生成答案 JSON，写入 `./outputForLocomo/output_locomo_{user_id}.json`；每题后 `clearMemoryWindow`。  
- **入口**：命令行 `--user_id`。

### 10. `Core/eval.py`

- **定位**：**评测指标库** `LocomoEvaluator` + 可选 **结果合并** 示例 `main`。  
- **指标**：单条预测的 F1、BLEU-1～4、以及可选的 LLM Judge（需配置 `api_key` / `api_url`）。  
- **`main`**：合并 `outputForLocomo/output_locomo_1.json`～`output_locomo_10.json` 为 `output_locomo_merged.json` 并跑批量评测统计。

---

## 四、模块依赖关系（简图）

```text
evalProcess.py / evalLocomo.py
        │
        ▼
    Core/AMA.py ─────────────► Model/model.py ──► Settings/config.py
        │                              │
        │                              └──► Settings/prompt.py
        ▼
StoreFunc/SQLite/sqliteFunc.py    StoreFunc/Faiss/faissFunc.py
                                        │
                                        └──► StoreFunc/Faiss/embedding.py
                                                  └──► Settings/config.py
```

---

## 五、小结

- **要做 Skill**：重点包装 `AMA` 类的生命周期与 `forwardUser` / `forwardRetrieve` / `clearMemoryWindow` / `clearAllMemory` 等接口，并把 `config` 与 `Store/` 路径外部化。  
- **要写论文/对齐 benchmark**：继续使用 `evalProcess.py`、`evalLocomo.py`、`eval.py` 与 LoCoMo 数据流。  
- **要与华为小艺 GUI Agent 结合**：在输入侧把 GUI 交互抽象为结构化「轮次」文本或 JSON，复用同一套存储与检索栈，再按需增加 GUI 专用 prompt 或轻量字段（本仓库当前以对话记忆为主）。

---

*文档生成依据：仓库内 `AdaptiveMemory` 目录当时源码结构；若后续增删文件，请同步更新本节路径与说明。*
