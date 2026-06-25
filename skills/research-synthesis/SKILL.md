---
name: research-synthesis
description: |
  Synthesizes a grounded, multi-source answer from retrieved knowledge-base
  passages. Use this skill when the user asks a conceptual or "explain / compare /
  how does X work" question that benefits from combining several sources into a
  structured answer with citations.
  Do NOT use for one-line factual lookups, for saving notes, or for formatting an
  already-written answer.
version: 1.0.0
license: MIT
allowed-tools: [search_knowledge_base]
metadata:
  author: defne
---

# Research Synthesis

## When to use
- "Explain how MCP reduces the N x M integration problem."
- "Compare Agent Skills with MCP — when do you use each?"
- Any question where a good answer draws on more than one passage.

## When NOT to use
- Simple factual lookups answerable from a single sentence.
- Requests to save, format, or cite an already-finished answer.

## Workflow
1. Call `search_knowledge_base` with the user's question (and a rephrasing if
   the first result set is thin). Prefer breadth: retrieve a few passages.
2. Read the retrieved passages. Identify the 2-4 ideas that actually answer the
   question; ignore tangential chunks (they are distractor noise).
3. Write the answer in this shape:
   - One-sentence direct answer.
   - 2-4 short supporting points, each grounded in a retrieved passage.
   - A trade-off / nuance sentence when the sources disagree or add caveats.
4. Cite sources inline as `[source: <filename>]` using the `source` field
   returned by the tool. Never cite a source you did not retrieve.

## Quality bar
- If retrieval returns nothing relevant, say so plainly instead of inventing an
  answer. A grounded "I don't have that in the knowledge base" beats a fluent
  hallucination.
- Keep it tight — the goal is signal, not length.
