# The Harness vs. the Model

An AI agent is two things: a **model** (the reasoning engine, behind a remote
API) and a **harness** (the deterministic engineering around it that turns a
text generator into a reliable system).

## The model is becoming commoditized; the harness is the asset

A reverse-engineering of Claude Code v2.1.88 found that **98.4% of the codebase
is operational infrastructure** — permission classifiers, context compaction,
subagent delegation, session storage — and only **1.6% is the agent loop
itself**. As foundation models converge on baseline reasoning, the differentiator
for autonomous reliability becomes the engineering around the model.

## What's inside an agent runtime

The agent loop has converged across vendors: maintain a conversation, call the
model, execute tools, read files, return a response. Concretely the harness is
responsible for:

- **Tool discovery & dispatch**: present available tools to the model, parse the
  model's tool calls, execute them, feed results back.
- **Permission / approval gating**: decide which actions can run automatically
  and which need a human (HITL).
- **Context management**: keep the active context small (progressive disclosure,
  compaction) because every token competes for attention.
- **Audit & observability**: log every tool call and decision for debugging and
  governance.
- **Loop control**: bound the number of steps; detect completion; handle errors.

## Single-agent monolith -> specialization

A "Swiss Army knife" single agent with many tools hits a ceiling: the larger its
tool set, the worse its decisions, because the search space for the next action
is too large. Two ways out:

- **Internal specialization (still a monolith)**: partition into focused
  sub-agents that share one runtime/memory. Reduces search space, mitigates
  attention dilution, keeps a high signal-to-noise context.
- **Distributed multi-agent**: specialists across network boundaries, connected
  by the A2A protocol. Right when you have genuine parallelism, real capability
  boundaries, or heterogeneous models.

But many systems built multi-agent by default can be simplified to one
general-purpose agent plus a **skills library** — you maintain skills, not
deployments.

## Tools vs. specialists (the GOTO problem)

A tool is a passive, fire-and-forget instrument with a bounded contract. A
specialist agent operates in an unbounded problem space and may pause, ask for
clarification, and resume — like the difference between buying tools and hiring a
contractor. Forcing a collaborative agent into a tool wrapper injects the
equivalent of a GOTO into your orchestrator. Keep the tool layer (MCP) clean and
structured; route messy multi-turn collaboration through the A2A layer.
