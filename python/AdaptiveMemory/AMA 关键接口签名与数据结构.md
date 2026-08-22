# AMA 关键接口签名与数据结构

本文档基于 `Core/AMA.py` 精读整理，供将 AMA 封装为 OpenClaw 等可安装 Skill 时使用。表结构细节可参考 `StoreFunc/SQLite/sqliteFunc.py`，FAISS 路径规则见 `StoreFunc/Faiss/faissFunc.py`。

---

## `AMA.__init__`

### 签名

```python
def __init__(
    self,
    user: str,
    memoryWindowSize: int = 1e5,
    memoryWindowLength: int = 20,
    modelMemory: str = "gpt-4o-mini",
    temperature: float = 0.0,
    turnRetrieve: int = 1,
):
```

### 参数

| 名字 | 类型 | 含义 |
|------|------|------|
| `user` | `str` | 命名空间标识：主对话表名即为该字符串；事实表为 `{user}Fact`，篇章表为 `{user}Episode`，句子表为 `{user}Sentence`；FAISS 文件前缀同为 `user`。 |
| `memoryWindowSize` | `int` | 短期记忆窗口的** token 预算**上限（与 `adjustMemoryWindow` 联动，默认 `100000`）。 |
| `memoryWindowLength` | `int` | 窗口内**最多保留的条数**（超过 `length * 2` 或 token 超限会触发从左侧淘汰）。 |
| `modelMemory` | `str` | 传给 `model.memoryAgent` 的模型名，用于 Retrieve / Judge / Construct / Episode 等推理调用。 |
| `temperature` | `float` | **当前实现中未赋给 `memoryAgent`**：`AMA` 内写死 `model.memoryAgent(..., temperature=0.0)`，该形参可视为预留。 |
| `turnRetrieve` | `int` | Judge 返回「需多轮补充检索」(`operator == 9`) 时，内部 while 循环的**最大额外检索轮数**上界（与 `forwardUser` / `forwardRetrieve` 中逻辑一致）。`evalLocomo.py` 示例中传入 `3`。 |

### 返回值

无（Python 构造函数）。

### 副作用（昂贵操作）

1. **SQLite**：`sqliteFunc.createDb()` 确保 `Store/` 与 `Store/AMA.db`；为当前 `user` 创建（若不存在）四张逻辑表：主表 `{user}`、事实 `{user}Fact`、篇章 `{user}Episode`、句子 `{user}Sentence`。
2. **FAISS**：`makeTwoTypesIndex` 创建或加载 `{user}_text_Index.faiss` 与 `{user}_fact_Index.faiss`；再 `loadFaissIndex(..., embedType="sentence")` 创建或加载 `{user}_sentence_Index.faiss`。
3. **状态字段**：初始化 `memoryWindow`（`deque`）、`memoryAgent`、`noDialogue`（根据主表最后一条 `dia_id` 推导下一对话段编号，如 `D1` / `D13`）、`indexEpisode`、`turnOfDialogue`、`retrieveContents` 等。

**不在 `__init__` 中**：不向 FAISS 批量灌向量（除非加载已有索引文件）；不调用 Embedding API 灌库。

### 典型调用示例

```python
memoryAgent = AMA(user=f"TaskClass{user_id}_Next")
# LoCoMo 问答评测中提高多轮检索次数：
memory = AMA(f"TaskClass{user_id}_Next", turnRetrieve=3)
```

（摘自 `Core/evalProcess.py`、`Core/evalLocomo.py`。）

---

## `forwardUser`

### 签名

```python
def forwardUser(self, userInput, showUsage: bool = False):
```

### 参数

| 名字 | 类型 | 含义 |
|------|------|------|
| `userInput` | `str` **或** `dict` | 用户本轮输入。若为 `dict`，开头会被 `json.dumps(..., ensure_ascii=False)` 转成字符串再参与后续 LLM 与 `json.loads`（构造写入路径会再解析）。 |
| `showUsage` | `bool` | 是否在各 `memoryAgent.inference*` 中打印 token 用量。 |

**当 `userInput` 为 `dict` 时，`evalProcess.py` 实际使用的 key**（均可选扩展，但构造 `rawData["content"]` 时依赖下列字段）：

| key | 类型 | 含义 |
|-----|------|------|
| `speaker` | `str` | 说话人（与 `text` 同时存在时，格式化为 `"{speaker}: {text}\n"` 写入主表 `content`）。 |
| `text` | `str` | 话语正文。 |
| `timestamp` | `str` | 会话时间标签（写入事实构造流水线；可与 session 级 `date_time` 一致）。 |
| `blip_caption` | `str`（可选） | 图像描述，存在则追加到 `content` 行。 |
| `query` | `str`（可选） | 图像相关 query，代码里写作 `img_query: ...` 追加。 |
| `img_url` | `str`（可选） | 图片 URL，追加到 `content`。 |

若缺少 `speaker`/`text` 结构，则整条 `userInput` 按字符串用于构造路径。

### 返回值

- **类型**：`str`
- **结构**：人工可读调试串，大致为  
  `"Retrieval results:\n" + json.dumps(retrievals) + "\nMemory Window:\n" + json.dumps(list(self.memoryWindow))`  
  （注意：返回时**尚未**把当前用户轮 append 进窗口；append 与 `adjustMemoryWindow` 在 `return` 之后执行，故字符串里的 Memory Window 是**更新前**的快照。）

### 副作用

- **LLM**：`inferenceRetrieve` → `inferenceJudge`（可能多轮）→ 条件触发 `inferenceRefresh` + `refresh`；并行 `inferenceJudgeEpisode` 与 `inferenceConstruct`；可能 `inferenceGenerateEpisode`。
- **SQLite 表**（与当前 `user` 绑定）：
  - `{user}Fact`：`constructFactWrite`
  - `{user}`（主表）：`constructFullWrite`
  - `{user}Episode`、`{user}Sentence`：`constructEpisodicWrite`（当 `inferenceJudgeEpisode` 的 `should_end == "true"` 字符串时）
  - `refreshUpdate` / `refreshDelete`：仅更新相关行的 `meta`（事实表、主表、篇章表链式 `updateMetaOnly`），**不删 FAISS 向量**
- **FAISS**：`constructFactWrite` → **fact** 索引；`constructFullWrite` → **text** 索引；`constructEpisodicWrite` → **sentence** 索引
- **`self.memoryWindow`**：在方法末尾 `append` 当前用户轮 `{"role":"user","content": userInput,"dia_id":...}`（`content` 仍为调用方传入的原始对象/字符串引用），并调用 `adjustMemoryWindow()`。
- **`self.turnOfDialogue`**：`+= 1`
- **`self.retrieveContents`**：设为本次 `retrievals`

### 典型调用示例

```python
temp_dict = {"speaker": speaker, "text": text, "timestamp": date_time}
# ... 可选 blip_caption / query / img_url
out = memoryAgent.forwardUser(temp_dict, showUsage=True)
```

（摘自 `Core/evalProcess.py`。）

---

## `forwardRobot`

### 签名

```python
def forwardRobot(self, robotOutput: str, showUsage: bool = False, timeInput: str = None):
```

### 参数

| 名字 | 类型 | 含义 |
|------|------|------|
| `robotOutput` | `str` | 助手本轮回复正文；写入主表 `content`，并参与 `inferenceConstruct`（`userInput` 前缀为 `"Assitant:" + robotOutput`）。 |
| `showUsage` | `bool` | 同上。 |
| `timeInput` | `str \| None` | 写入窗口项的 `time` 字段。若为 `"Unknown time"` 则改用当前时间；`None` 也用当前时间。 |

### 返回值

- **代码意图**：`dict`，含 `constructDecision` 与 `memoryWindow`。
- **现状**：当前 `Core/AMA.py` 中内部函数 `ConstructFactAndRaw` 使用未定义变量 `data` 调用 `constructFactWrite(data)`，且返回值未赋给 `construct_decision`，末尾 `output` 引用未定义变量，**按源码执行会异常**。Skill 改造时应按 `forwardUser` 中同名逻辑修正为 `constructFactWrite(factData)` 并明确返回值语义。

### 副作用（设计意图，与 `forwardUser` 构造段对齐）

- **SQLite / FAISS**：与 `forwardUser` 中 `constructFactWrite` + `constructFullWrite` 相同（事实表 + fact 索引；主表 + text 索引）。
- **不执行**：完整 Retrieve / Judge / Refresh 主流程（仅依赖已有 `self.retrieveContents` 传入 Construct）。
- **`self.memoryWindow`**：`append` `{"role":"assistant","content": robotOutput,"dia_id":...,"time": timeWindow}`，再 `adjustMemoryWindow()`。
- **`self.turnOfDialogue`**：`+= 1`

### 典型调用示例

评测脚本 `evalProcess.py` / `evalLocomo.py` **未调用** `forwardRobot`。集成助手轮记忆时可参照：

```python
# 设计用法（需先修复 AMA.py 内 forwardRobot 实现）
ama.forwardRobot("助手回复文本", showUsage=False, timeInput=None)
```

---

## `forwardRetrieve`

### 签名

```python
def forwardRetrieve(self, userInput: str, showUsage: bool = False, strongRetrieve: bool = False):
```

### 参数

| 名字 | 类型 | 含义 |
|------|------|------|
| `userInput` | `str` | 查询语句；直接交给 `inferenceRetrieve` 与检索通道。`evalLocomo.py` 传入 `question` 字符串。 |
| `showUsage` | `bool` | 同上。 |
| `strongRetrieve` | `bool` | 为 `True` 时**强制** `operator_r = 3`（双通道 text+fact，且后续可扩展 `episodes_results` 等），跳过模型对 `operator` 的取值。 |

### 返回值

- **类型**：`str`（**JSON 文本**）
- **结构**：`json.dumps` 后的对象，解析后形如：

```json
{
  "retrievals": <list 或 dict>,
  "memoryWindow": [ ... ]
}
```

- **`retrievals` 形态**：
  - `operator` 为 1 或 2：`list[dict]`，每条为 SQLite 行字典（主表或事实表字段，见下节「检索记录字典字段」）。
  - `operator` 为 3：`dict`，至少含 `text_match_results`、`fact_match_results`；多轮 Judge 后可能含 `episodes_results`（篇章记录列表）。
- **后处理**：在返回前会对部分字段做**破坏性处理**（`content` 拼接 `timestamp` 后删除 `timestamp`；双通道时还会 `pop` 部分键如 `fact`、`source`、`diaNO`），与 `forwardUser` 内打印用的原始 `retrievals` 不完全一致。

### 副作用

- **只读检索 + LLM Judge 循环**：不写 SQLite、不写 FAISS。
- **不修改** `self.memoryWindow`（仍会序列化当前窗口放入 JSON）。
- **不递增** `self.turnOfDialogue`。

### 典型调用示例

```python
memoInfo = memory.forwardRetrieve(question, showUsage=True, strongRetrieve=True)
result = chatExam.chat(question, memoryInfo=memoInfo, showUsage=True)
```

（摘自 `Core/evalLocomo.py`。）

---

## `judgeAndGenerate`

### 签名

```python
def judgeAndGenerate(self):
```

### 参数

无。

### 返回值

- **类型**：`None`（函数无 `return` 语句）。

### 副作用

- 读取主表最后一条 `queryLastRecord(self.user)`，与篇章表最后一条比较 `episode` 字段与篇章 `id`；若不一致，调用 `inferenceGenerateEpisode(..., "The dialogue ends.", ...)` 并 `constructEpisodicWrite`。
- **SQLite**：可能写入 `{user}Episode`、`{user}Sentence`。
- **FAISS**：可能更新 **sentence** 索引（句子级向量）。
- **不修改** `self.memoryWindow`。
- **注意**：若主表尚无记录，`resText` 为 `None` 时当前实现会**报错**；调用方应保证在已有至少一条主表写入后再调用，或 Skill 层做防护。

### 典型调用示例

```python
memoryAgent.judgeAndGenerate()
```

（摘自 `Core/evalProcess.py`，每个 `session` 对话循环结束后调用。）

---

## `clearMemoryWindow`

### 签名

```python
def clearMemoryWindow(self):
```

### 参数

无。

### 返回值

`None`。

### 副作用

- 将 `self.memoryWindow` 设为 **`[]`（空列表）**。
- **实现注意**：`__init__` 使用的是 `collections.deque`，而 `adjustMemoryWindow` 使用 `popleft()`。若在**非空窗口**上把 `memoryWindow` 换成 `list` 后再触发收缩逻辑，会 `AttributeError`。`evalLocomo.py` 在每题后清空窗口且主要只用 `forwardRetrieve`，通常窗口保持空，故评测路径未必触发该问题。Skill 改造时建议改为 `self.memoryWindow.clear()` 或重新赋值为 `deque()`。

### 典型调用示例

```python
memory.clearMemoryWindow()
```

（摘自 `Core/evalLocomo.py`，每道 QA 后调用。）

---

## `clearAllMemory`

### 签名

```python
def clearAllMemory(self):
```

### 参数

无。

### 返回值

`None`。

### 副作用

- **SQLite**：`deleteTable` 删除 `{user}`、`{user}Sentence`、`{user}Episode`、`{user}Fact` 四张表。
- **FAISS**：`deleteUserFaissIndices(self.user)` 删除该 `user` 的 text / fact / sentence 三个索引文件（若存在）。
- **`self.memoryWindow`**：调用 `clearMemoryWindow()`，同上变为 `[]`。

---

## 附录：内部 LLM 决策 dict 常用 key（非 `forward*` 形参，但影响行为）

由 `Model/model.py` 解析 JSON 得到，供 Skill 调试对照：

| 来源 | 常用 key | 类型 | 含义 |
|------|-----------|------|------|
| `inferenceRetrieve` | `operator` | `int` | 1 fact 单通道 / 2 text 单通道 / 3 双通道 |
| | `retrieveQuery` | `str` | 检索查询句 |
| | `topK` | `int` | Top-K |
| `inferenceJudge` | `operator` | `int` | 如 `-1` 通过、`-2` 冲突触发 refresh、`9` 多轮补充检索等（与 `prompt.judgePromptEN` 约定一致） |
| `inferenceConstruct` 输出 / `constructFactWrite` 输入 | `facts` | `list` | 元素为 `{"content": str}` |
| | `timestamp` / `source` / `related_id` / `meta` | 各类 | 写入事实批处理与主表 |
| `inferenceRefresh` | `operator` | `int` | `4` 更新 / `5` 删除 |
| | `dataList` | `list` | 每项含 `id`；更新时尚需 `new_content` |
| | `timestamp` | `str` | 写入 meta 描述 |
| `inferenceJudgeEpisode` | `should_end` | 常为字符串 `"true"` / `"false"` | 代码用 `== "true"` 判断 |
| | `reason` | `str` | 传给篇章生成 |
| `inferenceGenerateEpisode` | `title` / `content` / `timestamp` | `str` | `constructEpisodicWrite` 使用 `content` 等 |

---

## 附录：检索结果行字典（`queryByIdList`）主要字段

- **主表 `{user}`**：`id`, `content`, `fact`, `source`, `related_id`, `dia_id`, `timestamp`, `episode`, `meta`（`related_id` 可能被解析为 JSON）。
- **事实表 `{user}Fact`**：`id`, `content`, `diaNO`, `dia_id`, `timestamp`, `meta`。
- **篇章表 `{user}Episode`**：`id`, `content`, `meta`（`content` 内常为整条 JSON 字符串）。
- **句子表 `{user}Sentence`**：`id`, `content`, `episodeID`。

---

# A. AMA 实例生命周期与复用

1. **一个 `AMA` 实例对应几个 user？**  
   **一个实例绑定一个 `user` 字符串**。该字符串同时决定 SQLite 表名前缀与 FAISS 文件名前缀；不同 user 应对应不同实例（或不同进程/配置），否则表与索引会混用同一命名空间。

2. **`__init__` 昂贵操作**  
   连接/创建 `AMA.db`、创建 4 张表（若不存在）、加载或新建 3 个 FAISS 索引文件、查询最后一条对话以恢复 `noDialogue`。会读盘；**不会**在初始化时批量调用 Embedding 写入向量。

3. **实例可否复用？**  
   **可以且推荐**：同一评测人物或同一终端用户会话内复用同一 `AMA(user=...)`，以保持 `memoryWindow`、`noDialogue`、`turnOfDialogue` 与库内状态连续。跨实验若需干净状态应 `clearAllMemory()` 或换 `user` 标识。

---

# B. `Store/` 目录下生成文件一览

| 路径模式 | 含义 | 创建/写入触发点 |
|----------|------|-----------------|
| `Store/AMA.db` | 单库文件，多 user 多表 | `sqliteFunc.createDb()`；各 `insert`/`construct*`/`refresh*` |
| `Store/{user}_text_Index.faiss` | 主表正文向量 | `makeTwoTypesIndex` / `loadFaissIndex`；`constructFullWrite` → `addToFaissIndex(..., embedType="text")` |
| `Store/{user}_fact_Index.faiss` | 事实句向量 | `makeTwoTypesIndex`；`constructFactWrite` → `addBatchToFaissIndex` |
| `Store/{user}_sentence_Index.faiss` | 句子级向量（篇章拆分） | `__init__` 中 `loadFaissIndex(..., "sentence")`；`constructEpisodicWrite` → `addBatchToSentencesIndex` |

**文件名规则**：固定目录 `Store/`；`AMA.db` 为全局库名；FAISS 为 **`{user}` + 下划线 + `{text|fact|sentence}` + `_Index.faiss`**，其中 `{user}` 与构造 `AMA(user="...")` 时字符串完全一致（区分大小写）。

**删除**：`clearAllMemory()` 删除上述三张 FAISS 与四张表；**不删除**整个 `AMA.db` 文件（其他 user 的表仍在同一库中）。

---

*文档生成自 `Core/AMA.py` 及关联模块；若上游修正 `forwardRobot` / `clearMemoryWindow` 实现，请同步更新本节与副作用描述。*
