---
name: note-taking
description: |
  Persists a short, useful note for the user via the save_note action tool. Use
  this skill when the user explicitly asks to save, remember, bookmark, or write
  down a fact, takeaway, or follow-up.
  Do NOT use for answering questions, retrieving information, or summarizing
  unless the user also asks to save the result.
version: 1.0.0
license: MIT
allowed-tools: [save_note]
metadata:
  author: defne
---

# Note Taking

## When to use
- "Save this: MCP uses JSON-RPC 2.0 over stdio or Streamable HTTP."
- "Remember that I want to revisit the A2UI security model."

## When NOT to use
- Any request that is purely a question or retrieval.

## Workflow
1. Distil what the user wants saved into one or two crisp sentences. Do not save
   the entire conversation.
2. Call `save_note` with a short `title` and the `content`.
3. Because `save_note` is an **action** tool (it writes to disk), it is gated by
   the human-in-the-loop approval step. Present the exact note you intend to save
   and let the approval gate confirm before it is written.
4. After it is saved, confirm with the returned note id.

## Anti-patterns
- Don't silently save things the user didn't ask to save.
- Don't paraphrase so aggressively that the saved note loses the user's meaning.
