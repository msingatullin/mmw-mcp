# MMW agent instruction presets

Example instructions that tell coding agents (Claude Code, Codex, Cursor and other MCP clients) when to use MMW memory. Adapt them to your project.

## 1. Secrets

MMW redacts secrets (API keys, tokens, passwords) before storage: on the server for every record, and additionally on your computer for session history uploaded by `mmw-agent`. Still, instruct agents not to store credentials in the first place.

The `.mmwignore` file in this repository is an example convention for your own agent instructions. **It is not read or enforced by the MMW server or by `mmw-agent`.**

## 2. Cursor (`.cursorrules`)

```markdown
# Persistent Memory Protocol (MMW)
- Before complex refactoring, query earlier architecture decisions with the MMW `search` tool
  (for example query="architecture decisions").
- When a critical decision, API contract or bugfix milestone is verified, store it with `remember`
  (content="[MILESTONE] Verified fix for ...", fact_key="milestone-name").
- Never store credentials, raw tokens or .env contents.
```

## 3. Claude Code / Codex (`CLAUDE.md`, `AGENTS.md`)

```markdown
## Memory guidelines
1. Check context with MMW `search` before asking repetitive questions about project architecture.
2. Record permanent requirements and decisions with MMW `remember`.
3. Pass `source_id` / `source_hash` and `fact_key` where possible, so records can be checked for freshness and conflicts
   and conflicting facts are detected.
```

Full tool reference: [README.md](README.md#mcp-tools) and https://app.mmwhub.tech/help/user/quickstart.
