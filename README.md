# MMW (Managed Memory Workspace) — MCP connection kit

[![smithery badge](https://smithery.ai/badge/mmsingatullin/mmw)](https://smithery.ai/servers/mmsingatullin/mmw)
[![MMW MCP connector](https://glama.ai/mcp/connectors/tech.mmwhub.mcp/mmw/badges/score.svg)](https://glama.ai/mcp/connectors/tech.mmwhub.mcp/mmw)
[![Protocol](https://img.shields.io/badge/MCP-Streamable%20HTTP-blue?style=flat-square)](https://modelcontextprotocol.io)
[![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)](LICENSE)

Connection guides and client configuration for [MMW](https://mmwhub.tech).

User documentation: **https://app.mmwhub.tech/help/user/quickstart**

---

## What MMW is

MMW is a memory server for the Model Context Protocol (MCP). Your agent (Claude, Codex, Cursor or any MCP client) stores facts, decisions and agreements in MMW and finds them again in later sessions. Memory is not tied to one model or one computer.

Every user has a personal space. Companies create organizations: units, roles, visibility rules and knowledge handover when someone leaves.

Components:

- **Memory server:** `https://mcp.mmwhub.tech/mcp` — MCP over Streamable HTTP, stateless (every request stands on its own), JSON responses, API key authentication.
- **Local agent `mmw-agent`:** connects your MCP client to the server over stdio and, only with your consent, uploads Claude Code and Codex session history.
- **Account:** https://app.mmwhub.tech — API keys, projects, memory records, organizations, plan.

What MMW does not do:

- It does not read your conversations on its own: memory contains what your agent saved with `remember`, plus the sessions you explicitly allowed to upload.
- **Search over uploaded sessions and automatic fact extraction from them are not available yet.** Sessions are stored but do not appear in search results.
- It does not keep secrets: keys, tokens and passwords are replaced with placeholders before anything is stored.

---

## Quickstart

1. Sign up at https://app.mmwhub.tech and confirm your email.
2. Choose a plan. Free is a 3-day trial, no card required.
3. Copy your API key (it starts with `mmw_`). It is shown once — store it in a password manager.
4. Connect your client (below), restart it, and ask the agent: *"Remember in MMW: staging is deployed with the systemd unit app-staging."* In a new session: *"Search MMW for how to deploy staging."*

### Recommended: the local agent `mmw-agent` (Claude Code, Claude Desktop, Cursor, Codex)

Requirements: Python 3.11+ and [uv](https://docs.astral.sh/uv/) (the `uvx` command). The agent is not published on PyPI; `uvx` fetches the wheel on first start:

```
https://app.mmwhub.tech/downloads/mmw-agent/mmw_agent-0.1.3-py3-none-any.whl
```

**Claude Code**

```bash
claude mcp add mmw \
  -e MMW_API_KEY=mmw_your_key \
  -e MMW_ENDPOINT=https://mcp.mmwhub.tech \
  -- uvx --from https://app.mmwhub.tech/downloads/mmw-agent/mmw_agent-0.1.3-py3-none-any.whl mmw-agent
```

Or add the `mcpServers.mmw` block below to `~/.claude.json` by hand.

**Claude Desktop and Cursor** — the same JSON block: for Claude Desktop in `claude_desktop_config.json` (Settings → Developer → Edit config), for Cursor in `~/.cursor/mcp.json`.

```json
{
  "mcpServers": {
    "mmw": {
      "command": "uvx",
      "args": [
        "--from",
        "https://app.mmwhub.tech/downloads/mmw-agent/mmw_agent-0.1.3-py3-none-any.whl",
        "mmw-agent"
      ],
      "env": {
        "MMW_API_KEY": "mmw_your_key",
        "MMW_ENDPOINT": "https://mcp.mmwhub.tech"
      }
    }
  }
}
```

**Codex** — `~/.codex/config.toml`:

```toml
[mcp_servers.mmw]
command = "uvx"
args = ["--from", "https://app.mmwhub.tech/downloads/mmw-agent/mmw_agent-0.1.3-py3-none-any.whl", "mmw-agent"]
env = { MMW_API_KEY = "mmw_your_key", MMW_ENDPOINT = "https://mcp.mmwhub.tech" }
```

After a restart the client shows `remember`, `search`, `forget`, `validate_memory`, `gateway_call` and `mmw_sync_status`.

Check from a terminal:

```bash
MMW_API_KEY=mmw_your_key MMW_ENDPOINT=https://mcp.mmwhub.tech \
  uvx --from https://app.mmwhub.tech/downloads/mmw-agent/mmw_agent-0.1.3-py3-none-any.whl mmw-agent status
```

#### Agent commands

| Command | What it does |
| :--- | :--- |
| `mmw-agent` | Runs as an MCP server over stdio (this is how your client starts it). |
| `mmw-agent consent` | Allow uploading session history. Interactive terminal only; a person must answer. |
| `mmw-agent revoke` | Withdraw consent: uploads stop immediately. |
| `mmw-agent status` | Local consent state and how many sources the server already has. |

#### Agent environment variables

| Variable | Purpose |
| :--- | :--- |
| `MMW_API_KEY` | API key from your account (required). |
| `MMW_ENDPOINT` | Server address. Set `https://mcp.mmwhub.tech`. |
| `MMW_LANG` | Message language, `en` or `ru` (default depends on the server address). |
| `MMW_AGENT_HOME` | Agent state directory, default `~/.mmw`. |

The agent forwards every call to the server, so the client sees the full list of server tools. If the server is unreachable at start-up, the client does not fail: the agent answers locally and connects when the server is back.

### claude.ai (web) — OAuth connector

1. Settings → Connectors → Add custom connector.
2. URL: `https://mcp.mmwhub.tech/mcp`
3. On the MMW authorization page paste your API key and choose Allow. Claude receives its own 30-day token (OAuth with PKCE); your key is not shared with claude.ai.

The local agent does not run in the web app, so session sync is not available there.

### Any other MCP client — direct remote HTTP

If your client (for example VS Code or another MCP client) supports remote MCP servers over Streamable HTTP, connect without the agent:

```json
{
  "mcpServers": {
    "mmw": {
      "url": "https://mcp.mmwhub.tech/mcp",
      "headers": { "Authorization": "Bearer mmw_your_key" }
    }
  }
}
```

The exact key names (`url`, `headers`) differ between clients; check your client's MCP documentation. Session sync and `mmw_sync_status` are only available through `mmw-agent`.

---

## MCP tools

| Tool | Where | Description |
| :--- | :--- | :--- |
| `remember` | server | Store a memory record. |
| `search` | server | Find records by query. |
| `forget` | server | Delete a record or all records of a source. |
| `validate_memory` | server | Check records of a source against its current hash. |
| `gateway_call` | server | Call a tool of an integration connected to the key's project. |
| `mmw_sync_status` | `mmw-agent` only | Read-only: whether session-sync consent was given and how the last sync cycle went. |

Integrations connected to a project (for example `github_readonly`) may also appear as tools, but only for keys of that project.

### `remember`

| Parameter | Description |
| :--- | :--- |
| `content` | Record text (required). |
| `workspace` | Workspace, default `default`. |
| `scope` | Label for filtering (`shared`, `private`, …). It does not restrict access; in organizations access is governed by visibility. |
| `source`, `source_id`, `source_hash`, `source_revision` | Where the record comes from; with `source_hash` the record is verified. |
| `fact_key` | Fact key: records with the same key are compared for conflicts. |
| `confidence` | 0–1, default 0.5. |

The `X-Idempotency-Key` header makes retries safe: the same key with the same content returns the same record.

### `search`

| Parameter | Description |
| :--- | :--- |
| `query` | Query text. |
| `workspace` | Workspace. |
| `scope` | Label filter. |
| `limit` | 1–50, default 10. |
| `current_source_hash` | Fresh source hash: outdated records become `stale`. |
| `exclude_stale` | Hide outdated records. |

Returns records with source, confidence, status (`verified`, `unverified`, `stale`, `conflict`) and graph links (`graph_relations`).

### `forget`

`memory_id` deletes one record; `source_id` deletes every record of that source. Deleted records leave search and graph links; the deletion is kept for audit. In an organization you can only delete what you can see.

### `validate_memory`

`source_id` and `current_source_hash`: how many records of the source were checked, which are stale and which conflict.

### `gateway_call`

`server`, `tool`, `arguments`: calls a tool of a connected integration on behalf of the project. Integration secrets stay on the server and never reach the agent. Integrations are enabled in the account under MCP Gateway.

---

## Session sync (opt-in, `mmw-agent` only)

- **Consent:** without consent not a single byte leaves your computer. Run `mmw-agent consent` in a terminal: the agent shows how many sessions it found and asks for permission. A model or a script cannot give consent. Stop at any time with `mmw-agent revoke`.
- **Uploaded:** user and assistant messages, tool calls, tool results up to 4,000 characters, from Claude Code and Codex.
- **Not uploaded:** model reasoning, system prompts, token counters, file snapshots, file paths.
- **Secrets** (API keys, tokens, passwords) are replaced on your computer before upload and again on the server.
- **Reliability:** the server remembers up to which byte it accepted each file. After a network drop, a restart or a server restore, the agent sends what is missing. If the server is temporarily low on space, the agent waits and resumes later.
- **Not available yet:** search over uploaded sessions and extracting facts from them into memory. Today sessions are stored (compressed) but do not appear in search results.

Session history volume by plan (newest sessions first; counted on the cleaned text):

| Plan | History volume | Depth |
| :--- | :--- | :--- |
| Free | 25 MB | 7 days |
| Starter | 100 MB | 30 days |
| Pro | 500 MB | 90 days |
| Enterprise and organizations | 20 GB | full history |

---

## Organizations

- **Spaces:** one login, one personal space and any number of organizations, with a switcher in the account. An organization never becomes the default space. The organization cannot see the personal space.
- **Structure:** holding / legal entity / branch / department / unit / team.
- **Roles:**

| Role | Rights |
| :--- | :--- |
| Admin | Structure, people, invitations, all keys (never their secrets), audit log, plan. |
| Head | Records of their unit and everything below it; offboarding people in that subtree. |
| Member | Own records and records opened to their unit, project or the organization. |
| Contractor | Own records and project records only; access can be time-limited. |
| Auditor | Organization audit log without record content. |

- **Visibility of a record:** author only (draft), unit (and everything below it), project, whole organization. The rule is enforced on the server on every read path: search, validation, deletion, graph links, the account and the archivist. A head does not see drafts of a person who still works there.
- **Invitations:** a one-time link for a specific email, valid for 7 days. Emails are not sent yet — the admin passes the link on.
- **Member keys:** members issue their own keys. Admins see the list and can revoke any key, but can never reveal or rotate someone else's key.
- **Offboarding:** an admin or the head of the unit picks who receives the knowledge. The person's keys are revoked immediately. The recipient sees all of their records, drafts included, in the account and through their own agent, and can open them to the unit or the organization.
- **Contractor terms:** a term in days (1–365). After the term the person cannot read or write anything and the seat is not billed. Extensions are logged.
- **Audit log:** offboarding start and completion, reads of handed-over knowledge (account and MCP), visibility changes, access-term changes. Never record content.
- **Not available:** SSO/SAML, email delivery of invitations, automatic billing for organizations, sharing between legal entities of a holding, directory imports.

Organizations are activated by the MMW team: contact support@mmwhub.tech.

---

## Plans

| Plan | Price | Records | Calls/min |
| :--- | :--- | :--- | :--- |
| Free | $0, 3-day trial | 250 | 60 |
| Starter | $5/month | up to 5,000 per project | 120 |
| Pro | $35/month | up to 100,000 | 120 |
| Enterprise | $117/month (SLA, NDA) | up to 1,000,000 | 300 |
| On-premise | contact us | by agreement | — |

**Organizations:** $18 per seat per month, or $14 per seat per month billed yearly; minimum 5 seats. People who left and contractors whose term ended take no seat. Pilot: 14 days, up to 10 seats.

When a limit is reached, writes are refused with a clear error; reading keeps working.

---

## Security

- **Redaction:** secrets (API keys, tokens, passwords) are replaced with placeholders before storage, in records and in sessions. Records that look like an attempt to inject instructions into agent memory are rejected.
- **Isolation:** accounts, projects and workspaces are isolated; inside an organization the visibility rules above apply.
- **Keys:** shown once; the server keeps only a hash (PBKDF2) plus a lookup index. Revocation takes effect immediately.
- **Logs:** MCP operation logs never contain record text.
- **Transport:** stateless Streamable HTTP; every request is authenticated on its own, so nothing needs to reconnect after a pause.
- **Backups:** nightly, compressed, the last 7 kept plus an off-server copy. Content (records and sessions) is backed up on Enterprise and for organizations; system data (account, payments, keys, projects) on every plan.

---

## Connect Kit (`connect.sh`, `connect.ps1`)

The scripts write a **direct remote connection** (`url` + `Authorization` header) into your client configuration and can verify it with `--verify`. They do not install `mmw-agent` and do not enable session sync. Default endpoint: `https://mcp.mmwhub.tech/mcp`.

```bash
# macOS / Linux — preview first
MMW_CREDENTIAL='mmw_your_key' ./connect.sh --client cursor --dry-run
MMW_CREDENTIAL='mmw_your_key' ./connect.sh --client cursor --verify

# Windows (PowerShell)
$env:MMW_CREDENTIAL='mmw_your_key'
.\connect.ps1 -Client cursor -Verify
```

**Warning — read before running `connect.sh`:**

- Without `--client`, it configures **every client it detects** on the machine.
- `--client codex` **overwrites `~/.codex/config.toml` entirely** with a single `[mcp_servers.mmw]` block; any other Codex settings in that file are lost. Back the file up first, or add the Codex block from the Quickstart by hand.
- `--client claude` also **appends an "MMW Omnipresent Memory" instruction block to `~/.claude/CLAUDE.md`** (if that file exists and does not already contain it), and, if `mmw_proxy.py` is found, registers it in Claude Code CLI as a stdio server.
- The key is stored in `~/.config/mmw/credential` (mode 600) and written in plain text into the client configuration files.
- `--uninstall` deletes the generated client configuration files (not just the `mmw` entry) and the stored key.

`connect.ps1` writes the client configuration file for the chosen client from scratch and, for Codex, only prints the block to add.

---

## Legacy: `mmw_proxy.py`

`mmw_proxy.py` is an earlier local stdio proxy with a local SQLite spool. It is **legacy and no longer maintained**: it exposes only `remember`, `search`, `forget` and `spool_status`, does not support `validate_memory`, `gateway_call` or session sync. Use `mmw-agent` instead.

---

## Links

- Website: https://mmwhub.tech
- Account and API keys: https://app.mmwhub.tech
- User documentation: https://app.mmwhub.tech/help/user/quickstart
- MCP endpoint: https://mcp.mmwhub.tech/mcp
- Smithery: https://smithery.ai/servers/mmsingatullin/mmw
- Support: support@mmwhub.tech

## License

MIT, see [LICENSE](LICENSE).
