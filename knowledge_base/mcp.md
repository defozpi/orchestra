# Model Context Protocol (MCP)

MCP is an open standard introduced by Anthropic in November 2024. It is the
"USB-C" of agent harnesses: a single, plug-and-play socket that connects models
to databases, filesystems, and web APIs without writing a bespoke connector for
every pairing.

## The N x M integration problem

Without a standard, connecting N models to M tools requires O(N x M) custom
integrations. With 5 models and 10 tools you maintain 50 fragile connectors, and
a single upstream API change can break many of them. MCP reduces this to
O(N + M): each model speaks MCP once, each tool exposes MCP once.

## Architecture: Hosts, Clients, Servers

MCP uses a client-server model inspired by the Language Server Protocol.

- **Host**: the application that manages clients, orchestrates tool use, and
  enforces security policies and guardrails.
- **Client**: a component inside the host that maintains one connection to one
  server and manages the session lifecycle.
- **Server**: a program that advertises a set of tools (and optionally
  resources and prompts), receives commands, executes them, and returns results.

## Communication layer

The base message format is JSON-RPC 2.0. The four message types are Requests,
Results, Errors, and Notifications. Two transports are standard:

- **stdio**: the host launches the server as a local subprocess and exchanges
  JSON-RPC over stdin/stdout. Best for local development and prototyping.
- **Streamable HTTP**: the recommended remote transport; supports SSE streaming
  and stateless servers.

## Primitives

Server-offered: **Tools**, **Resources**, **Prompts**. Client-offered:
**Sampling**, **Elicitation**, **Roots**. In practice only Tools are broadly
supported (~99% of clients), so they are the core driver of MCP value.

## Tool definition fields

A tool conforms to a JSON schema: `name`, optional `title`, `description`,
`inputSchema`, optional `outputSchema`, and optional `annotations`. Treat
`description`, `inputSchema`, and `outputSchema` as effectively required — they
are how the model learns when and how to call the tool. Annotation hints include
`readOnlyHint`, `destructiveHint`, `idempotentHint`, and `openWorldHint`, but
these are only hints and must not be trusted from untrusted servers.

## Debugging MCP

When an agent hallucinates parameters or calls the wrong tool, debug the
transport directly rather than blindly tweaking the system prompt. Use the MCP
Inspector to view tool schemas and raw JSON-RPC packets, or Chrome DevTools to
trace SSE streams.

## Best practices for consuming MCP

Do: audit public servers before connecting; use RAG to load tools only when
needed; rely on internal/governed registries; show tool inputs to the user
before calling (human-in-the-loop); log tool usage for audit. Don't: build a
wrapper when you can consume an existing server; use unverified public servers
in production; hardcode credentials; connect to production data; grant
write/wide access when read-only and scoped access will do.
