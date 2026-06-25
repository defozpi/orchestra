# A2A, A2UI, and the Interoperability Stack

Open protocols turn an agent's harness from an isolated "custom machine" into a
modular, plug-and-play platform. The stack:

- **MCP** — the "USB-C": connect a model to tools, data, and APIs.
- **Agent Skills** — "playbooks": markdown instructions + scripts loaded on demand.
- **A2A (Agent-to-Agent)** — the "factory radio": specialized agents discover,
  negotiate, and delegate to each other.
- **A2UI (Agent-to-UI)** — the "generative display window": agents emit safe,
  interactive UI components instead of raw JSON.
- **AP2 / UCP** — the "transaction network": agents negotiate and execute
  commercial transactions within signed guardrails.

## A2A — a universal layer for a virtual workforce

As AI systems become distributed networks of specialists (Google, Salesforce,
ServiceNow, ...), each may be built in a different language and framework. A2A
(originally Google, now Linux Foundation) standardizes discovery and
communication so an orchestrator can collaborate with any specialist, agnostic
to how it was built — "just as HTTP standardized the web."

- **Agent Card**: the standardized machine-readable "CV" of an agent —
  capabilities, security/compliance, and interaction schemas.
- **Registries**: public marketplaces or private enterprise registries that turn
  agents into discoverable services.
- **Exposing an agent**: define the Agent Card, implement an Agent Executor
  (translation layer), and establish an A2A endpoint.

## A2UI — generative UI, done safely

Instead of returning raw JSON, an agent can describe a UI in a portable,
declarative format ("sheet music for UI") that any renderer (React, Flutter,
Lit, ...) performs natively. Safety comes from the agent only being able to
request components from a trusted catalog — it never ships executable code or
pre-rendered pixels. Two patterns: let the LLM emit the UI (intent-driven), or
have a tool return a fixed structure (input-driven, a server-side template).

## AP2 / UCP — agentic commerce

UCP is how the agent talks to a store (browse, customize, build an order). AP2 is
how it pays, using a signed "mandate" that encodes the user's rules ("spend up to
$25") so the agent can transact without exposing card details or exceeding limits.
