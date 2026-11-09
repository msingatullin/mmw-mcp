# MMW — shared memory across AI agents

**Shared memory across AI agents, with source-aware facts and visible conflicts.**

Save a decision in ChatGPT. Find the same record in Codex or linked Telegram. Keep its source and review conflicting information instead of copying context between chats.

[Get started](https://docs.mmwhub.tech/start/quickstart/) · [Create an account](https://app.mmwhub.tech/signup) · [Documentation](https://docs.mmwhub.tech/) · [Русский](README.ru.md)

[![MCP: Streamable HTTP](https://img.shields.io/badge/MCP-Streamable_HTTP-blue)](https://modelcontextprotocol.io/)
[![Client kit: MIT](https://img.shields.io/badge/client_kit-MIT-green)](LICENSE)

## What you can use

- **Shared memory:** connected clients save and retrieve records in the same authorized account, project and workspace. Client credentials need not be identical.
- **Sources and review:** attach `source_id` and other provenance fields. Conflicts, stale-source indicators and explicit fact review help distinguish saved claims from reviewed facts. An upload date or a model output does not establish factual currency.
- **MMW AI Archivist:** eligible new notes can be organized automatically. Privacy withdrawals and access rules apply. The AI assistant helps phrase conflict questions; the person makes the decision. See [processing boundaries](https://docs.mmwhub.tech/memory/archivist/).
- **Applications and teams:** integrate through MCP and use the account to manage records and access. Organization features require setup with MMW; they are not automatically enabled for every Free account.

MMW is a hosted platform. **This repository contains the public connection kit, not the private backend.** MIT applies to the files in this repository, not to a promise of an open-source hosted service.

MMW does not automatically read all your conversations or connect unrelated accounts. Local session uploads are separately opt-in. `scope=shared` is a search label, not an access grant. Source metadata is provenance, not proof of truth. Do not store credentials or rely on redaction as a guarantee that all secrets will be detected.

## Start in three steps

1. [Register and verify your email](https://app.mmwhub.tech/signup). The initial Free memory account is created automatically: a **3-day trial**, no payment card or initial paid-plan selection required.
2. Connect one supported client using one of the routes below. Connect the second client to the **same project**.
3. Save this invented note in the first client, then ask the second client to retrieve it:

```text
Save a separate MMW test note:
MMWFIRSTCHECK7429. Decision: prepare the team report on Fridays.
workspace=default, scope=shared, source_id=first-memory-check-7429.
Return the saved record ID.
```

```text
Use MMW to find MMWFIRSTCHECK7429 in workspace default.
Return its original ID and source_id. If unavailable, do not guess.
```

Compare the **record ID and source_id**. Similar wording alone is not a successful shared-memory test. In linked Telegram, use `/find MMWFIRSTCHECK7429`. Delete only the test record by its returned ID after checking.

### ChatGPT or a web connector: OAuth

Use the [official MMW ChatGPT app](https://chatgpt.com/plugins/plugin_asdk_app_6ac22b6361d481919cbaecd880a4c9ca), if available in your account. Authorize the intended project on MMW's page. No local agent is required. Availability depends on the client's plan and settings.

For other web clients that support remote MCP, use `https://mcp.mmwhub.tech/mcp` and follow their OAuth flow. [ChatGPT](https://docs.mmwhub.tech/clients/chatgpt/) · [Claude web](https://docs.mmwhub.tech/clients/claude-web/).

### Codex, Cursor or another remote MCP client

The endpoint is **`https://mcp.mmwhub.tech/mcp`**. Create a project key in the account and enter it through your client's protected local credential mechanism. Do not paste it into an assistant chat, a command committed to Git or a support log.

Codex reads TOML configuration; a direct connection can use an environment variable:

```toml
[mcp_servers.mmw]
url = "https://mcp.mmwhub.tech/mcp"
bearer_token_env_var = "MMW_API_KEY"
```

For a temporary Bash session, enter the value locally without putting it in shell history:

```bash
read -rsp 'MMW API key: ' MMW_API_KEY; echo
export MMW_API_KEY
codex
```

Use your client's protected credential storage for persistent use. JSON-based clients have a different configuration format. [Codex](https://docs.mmwhub.tech/clients/codex/) · [Cursor](https://docs.mmwhub.tech/clients/cursor/) · [All clients](https://docs.mmwhub.tech/clients/overview/).

### Optional local agent

For stdio-only clients or separately consented session uploads, use `mmw-agent`. Python 3.11+ and [uv](https://docs.astral.sh/uv/) are required. The wheel is distributed by MMW, not PyPI. The [agent guide](https://docs.mmwhub.tech/agent/overview/) is the canonical installation/version source; this README does not duplicate its release number.

Setup asks for the key locally. Session uploads are optional and are not required for `remember` or `search`. Review the upload scope before running `mmw-agent consent`; stop future uploads with `mmw-agent revoke`. Revoking uploads is distinct from deleting existing records or controlling server-side AI processing in Privacy.

## MCP reference

Read the actual `tools/list` for your connection. Catalog apps, direct MCP and the local agent may expose different subsets.

| Tool | Purpose |
| :--- | :--- |
| `remember` | Save a note with optional source and workspace metadata. |
| `search` | Retrieve authorized records; inspect provenance and conflict/stale annotations. |
| `validate_memory` | Compare source records with a supplied current source hash. |
| `forget` | Delete a record or authorized records of a source. |
| `preview_search`, `read_memory` | Bounded discovery and record reading, where exposed by the client profile. |
| `search_history` | Uploaded session search where supported by the connection and permissions. It does not grant access to unsynced chats. |

`gateway_call` and experimental external dispatch are **not part of the public Core memory workflow**. A retained tool schema is not evidence of an enabled integration. Local agent diagnostics are separate from server memory tools.

Example **tool arguments**, not standalone HTTP requests:

```json
{"content":"MMWFIRSTCHECK7429. Team report: Fridays.","workspace":"default","scope":"shared","source_id":"first-memory-check-7429"}
```

```json
{"query":"MMWFIRSTCHECK7429","workspace":"default","limit":5}
```

[Complete contracts](https://docs.mmwhub.tech/reference/mcp-tools/) · [Source and freshness](https://docs.mmwhub.tech/memory/source-and-freshness/) · [Shared-memory troubleshooting](https://docs.mmwhub.tech/guide/shared-memory/).

## Access, privacy and limits

Authorization and project/organization access rules apply to every connection. A client must be linked and authorized before it can read a record. Do not weaken permissions to make a demo succeed.

Review [data and deletion](https://docs.mmwhub.tech/account/data-and-deletion/) and [security](https://docs.mmwhub.tech/account/security/). Automatic organization can use external AI processing under the applicable service terms; privacy controls remain available. Model output does not automatically confirm a fact. Deleting live data and retention in an existing backup are separate operations.

The Free trial has finite limits. Paid plans also have limits; Enterprise is not an unlimited plan. Current prices, currencies, payment options and limits are in the account and on the [website](https://mmwhub.tech/#pricing). A release snapshot does not establish a recurring full-content backup entitlement for every plan. Do not use MMW as the sole backup of important information.

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

## Directories and distribution

- [Glama connector](https://glama.ai/mcp/connectors/tech.mmwhub.mcp/mmw)
- [Official MCP Registry](https://registry.modelcontextprotocol.io/?q=io.github.msingatullin%2Fmmw)

Directory descriptions may lag the live product. Their badges are directory metadata, not a latency, security or availability certification.

## Contribute

Use Fork → Branch → Pull Request for this public kit. Do not include API keys, private backend source or real memory contents. The public challenge tasks describe their own scopes; never probe other users or production without permission.

## Links and license

[Website](https://mmwhub.tech/) · [Account](https://app.mmwhub.tech/) · [Documentation](https://docs.mmwhub.tech/) · [Developer integration](https://docs.mmwhub.tech/developers/integrate/) · [Agent skill](https://docs.mmwhub.tech/memory/agent-skill/) · Support: support@mmwhub.tech

MIT for this client kit: [LICENSE](LICENSE).
