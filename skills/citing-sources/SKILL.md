---
name: citing-sources
description: |
  Enforces honest, verifiable citation discipline on any answer that uses
  retrieved material. Use this skill whenever the agent has called
  search_knowledge_base and is about to present claims drawn from those results.
  Do NOT use for casual conversation or for content the agent generated without
  retrieval.
version: 1.0.0
license: MIT
metadata:
  author: defne
---

# Citing Sources

## When to use
- After any retrieval, before presenting an answer that relies on it.

## When NOT to use
- Greetings, clarifying questions, or opinions not grounded in the knowledge base.

## Rules
1. Every factual claim that came from retrieval must carry a `[source: <file>]`
   marker, using the `source` metadata returned by the tool.
2. Never attribute a claim to a source whose passage does not support it. If you
   are unsure, drop the claim rather than mis-citing it — a wrong citation is
   worse than none.
3. If two sources conflict, cite both and note the disagreement.
4. End grounded answers with a short `Sources:` list of the unique files used.

## Why this matters
A citation the reader can verify is what separates a trustworthy assistant from a
plausible one. The reason isn't bureaucratic: ungrounded claims are exactly the
failure mode (context rot / hallucination) the whole RAG design exists to prevent.
