# 🛡️ MMW Security & Framework Presets

Managed Memory Workspace (MMW) provides enterprise-grade memory isolation and privacy controls for autonomous coding agents (Cursor, Claude Code, Windsurf, Cline).

## 1. Secret Protection (.mmwignore)
Always keep a `.mmwignore` in your project root. Autonomous agents automatically respect this boundary and will reject attempts to store credentials or environment variables into long-term memory:

```gitignore
.env*
*.key
*.pem
secrets.json
service-account*.json
```

## 2. Cursor System Prompt Preset (.cursorrules)
Place this snippet inside your `.cursorrules` to instruct the agent to leverage MMW persistent memory:

```markdown
# Persistent Memory Protocol (MMW)
- Before beginning complex refactoring, query historical architecture decisions:
  `mcp.search(query="architecture decisions")`
- Whenever a critical decision, API contract, or bugfix milestone is verified, persist it:
  `mcp.remember(content="[MILESTONE] Verified fix for ...", fact_key="milestone-name")`
- Never persist credentials, raw tokens, or .env contents.
```

## 3. Claude Code / Windsurf Agent Preset
In your agent instructions or `CLAUDE.md`:

```markdown
## Memory Guidelines
1. Check context using MMW `search` before asking repetitive questions about project architecture.
2. Record permanent requirements and decisions using MMW `remember`.
3. Always include provenance and fact_keys for verifiable audit trails.
```
