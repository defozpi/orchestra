# RAG, Context Rot, and the Token Budget

## Why retrieval-augmented generation

A foundation model can only generate from what it was trained on plus what is in
its request context. Retrieval-Augmented Generation (RAG) adds a retrieval step:
embed a corpus into a vector database, embed the user's query, fetch the most
similar chunks, and put only those chunks in the context. This grounds answers
in source material and lets the agent cite where information came from.

## The pipeline

1. **Chunk**: split documents into passages small enough to retrieve precisely
   but large enough to stay coherent (overlap preserves context across cuts).
2. **Embed**: map each chunk to a vector with an embedding model.
3. **Store**: upsert vectors + metadata into a vector DB (e.g. Qdrant).
4. **Retrieve**: embed the query, run nearest-neighbour search, return top-k
   chunks with their sources.
5. **Generate**: the model answers using only the retrieved context and cites it.

## Context rot — why you retrieve instead of dumping everything

Across 18 frontier models, performance degrades as input grows *even when task
difficulty is held constant*. "Lost in the Middle" shows accuracy is highest
when relevant info sits at the start or end of the context and sags in the
middle. The noise typical of real agent contexts (tool outputs, half-relevant
retrievals, intermediate reasoning) is among the worst for this.

Implications:

- **Capacity is the wrong metric.** A 1M-token window can degrade noticeably at
  50K tokens.
- **Active context is a budget, not a vessel.** Every token takes attention from
  every other; allocate it deliberately, like memory.
- **Keep active context small while keeping capability large.** RAG and
  progressive disclosure both do this: pull in only what the current turn needs.

## RAG for tools

The same idea applies to tools, not just documents. Don't load every tool schema
into context. Dynamically load tools from a registry only when needed and drop
them when the task is done, to prevent attention dilution.

## When NOT to reach for RAG

For ~100 process variants of the same job, one-agent-with-skills can beat running
a vector DB + embedding model + chunking strategy whose quality has nothing to do
with the actual procedures. Choose the lightest primitive that fits, and always
evaluate.
