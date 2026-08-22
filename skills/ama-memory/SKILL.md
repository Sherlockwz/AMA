---
name: ama-memory
description: Use AMA memory in OpenClaw to recall prior context, capture turns, inspect stored state, end sessions, or delete a user's memory when asked.
metadata:
  openclaw:
    homepage: https://sherlockwz.github.io/AMA/
---

# AMA Memory

AMA maintains three complementary forms of memory:

- raw text for exact details and wording;
- fact knowledge for stable, atomic information;
- episodes for high-level events and multi-turn summaries.

The plugin normally recalls and captures memory automatically. Use the explicit tools when a task needs deterministic memory handling or when diagnosing an integration.

## Operating rules

1. Prefer automatic recall for ordinary conversation. Do not call retrieval repeatedly when the injected `<ama-memories>` context already answers the request.
2. Use `ama_retrieve` before answering a question that clearly depends on earlier sessions and lacks sufficient recalled context.
3. Use `ama_process_turn` only for a user turn that should become long-term memory. Use `ama_process_assistant` for the corresponding assistant response.
4. Use `ama_session_end` when a conversation, topic, or work session has clearly ended so AMA can synthesize an episode.
5. Treat `ama_memory_forget` as destructive. Only invoke it after the user explicitly asks to delete or reset stored memory, and pass the intended `userId`.
6. Never expose API keys, database paths, internal record IDs, or unrelated stored memories in an answer.

## Tools

### `ama_retrieve`

Search without changing memory. Pass a concise, self-contained query. Enable strong retrieval only when the first retrieval is insufficient and multi-round verification is warranted.

### `ama_process_turn`

Process and store a user turn through retrieval, judging, refreshing, and construction. Use the actual user message rather than a paraphrase when wording or temporal details matter.

### `ama_process_assistant`

Store an assistant response after it has been delivered. This does not perform a second retrieval.

### `ama_memory_list`

Inspect memory counts and current window size. Use it for diagnostics, not as a substitute for semantic retrieval.

### `ama_session_end`

Trigger end-of-session episode generation after the final turn has been captured.

### `ama_memory_forget`

Erase all AMA memory for a user. Confirm intent and identity before invoking it.

## Typical workflow

```text
new user turn
  → auto-recall injects relevant AMA memories
  → answer using only relevant context
  → auto-capture stores the user and assistant turns
  → session end synthesizes episodic memory when appropriate
```

If automatic hooks are disabled, perform the same sequence explicitly with `ama_retrieve`, `ama_process_turn`, `ama_process_assistant`, and `ama_session_end`.

## Diagnostics

When tools are unavailable or the sidecar is unhealthy, ask the operator to run:

```bash
openclaw ama doctor
openclaw ama stats
```

Do not invent remembered content when retrieval fails. State that memory could not be checked and continue only with context available in the current conversation.
