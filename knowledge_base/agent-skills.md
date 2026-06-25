# Agent Skills

An Agent Skill is a folder containing a `SKILL.md` file plus optional `scripts/`,
`references/`, and `assets/` directories. It gives a general-purpose agent
on-demand specialist competence — turning one agent into many specialists
without context bloat. The format is an open standard (agentskills.io).

## Why skills spread so fast

1. **Too many instructions, worse results.** Dumping everything into one system
   prompt degrades the model (context rot). Skills load only on demand.
2. **Knowing how, not just what.** Skills are the first credible *procedural
   memory* primitive for LLM agents (vs. episodic and semantic memory).
3. **Multi-agent overload.** Many systems built multi-agent by default can be
   simplified to one general agent with a skills library.
4. **Portability.** A folder with a markdown file works in any agent with
   filesystem access.

## Progressive disclosure (the key idea)

Skills load in three levels:

1. **Metadata** (name + description) is always in context — tiny.
2. **SKILL.md body** loads only when the skill's description matches the task.
3. **Bundled resources/scripts** load strictly as needed; scripts run without
   polluting the token window.

This means 100 installed skills cost only ~100 x 50 = ~5,000 tokens of
always-loaded metadata, while keeping available capability effectively
unbounded. Anthropic has shown conversions cutting active context from ~150,000
tokens to ~2,000 (>98% reduction).

## The description is the routing algorithm

The description is the only thing the model sees when deciding to load a skill.
State what it does AND when to use it, front-load trigger keywords, and include
an explicit "do NOT use for ..." clause to prevent over-triggering. Aim for ~50
words. Naming: snake_case directories, kebab-case skill names, prefer the gerund
form (processing-pdfs), avoid generic names like utils/tools.

## Skill vs MCP vs AGENTS.md

- **Skill vs MCP**: they compose, not compete. MCP is *reach* (connect to a
  system); a Skill is *know-how* (how to think about a kind of work). A skill
  often tells the agent to call an MCP tool when it needs data.
- **Skill vs AGENTS.md**: AGENTS.md is always loaded (project conventions);
  skills load on demand. Use both.

## The five rules

1. One skill, one job. 2. Descriptions are an interface. 3. Skills are
dependencies — version, pin, review, test them. 4. The right team owns the right
skill. 5. The runtime is interchangeable — keep skills portable.
