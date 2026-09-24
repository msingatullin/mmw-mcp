# MMW (Managed Memory Workspace) — MCP Integration & Client Kit

[![smithery badge](https://smithery.ai/badge/mmsingatullin/mmw)](https://smithery.ai/servers/mmsingatullin/mmw)
[![MMW MCP connector](https://glama.ai/mcp/connectors/tech.mmwhub.mcp/mmw/badges/score.svg)](https://glama.ai/mcp/connectors/tech.mmwhub.mcp/mmw)
[![Protocol](https://img.shields.io/badge/MCP-Streamable%20HTTP-blue?style=flat-square)](https://modelcontextprotocol.io)
[![Latency](https://img.shields.io/badge/latency-%3C2ms-success?style=flat-square)](https://mmwhub.tech)
[![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)](LICENSE)

Official Model Context Protocol (MCP) connection kit and client configuration guides for [**MMW (Managed Memory Workspace)**](https://mmwhub.tech).

MMW provides ultra-fast (<2ms) persistent memory, tenant isolation, and cryptographic provenance for autonomous AI agents across sessions and tool executions.

---

## ⚡ Quickstart

MMW supports two connection modes:
1. **🛡 Local-First Resilient Spool (Recommended):** Zero data loss. Writes are persisted instantly (<1ms) to local SQLite (`~/.config/mmw/spool.db`) and synchronized in the background to MMW Cloud with automatic retries if offline or network fails.
2. **🌐 Direct Cloud Remote:** Connects directly via Streamable HTTP (`https://mcp.mmwhub.tech/mcp`).

---

## 💻 Client Configuration

### 🛡 Mode A: Local-First Resilient Spool (No data loss)

Run via standard Python MCP proxy:
```json
{
  "mcpServers": {
    "mmw": {
      "command": "python3",
      "args": ["-m", "mmw_mcp.spool_proxy"],
      "env": {
        "MMW_TOKEN": "<YOUR_MMW_API_KEY>"
      }
    }
  }
}
```

### 🌐 Mode B: Direct Remote MCP

#### 1. Claude Desktop (`claude_desktop_config.json`)
```json
{
  "mcpServers": {
    "mmw": {
      "url": "https://mcp.mmwhub.tech/mcp",
      "headers": {
        "Authorization": "Bearer <YOUR_MMW_API_KEY>"
      }
    }
  }
}
```

#### 2. Cursor (`~/.cursor/mcp.json`)
```json
{
  "mcpServers": {
    "mmw": {
      "url": "https://mcp.mmwhub.tech/mcp",
      "headers": {
        "Authorization": "Bearer <YOUR_MMW_API_KEY>"
      }
    }
  }
}
```

### 3. Zed Editor (`settings.json`)

```json
{
  "context_servers": {
    "mmw": {
      "endpoint": "https://mcp.mmwhub.tech/mcp",
      "headers": {
        "Authorization": "Bearer <YOUR_MMW_API_KEY>"
      }
    }
  }
}
```

### 4. Windsurf (`~/.codeium/windsurf/mcp_config.json`)

```json
{
  "mcpServers": {
    "mmw": {
      "serverUrl": "https://mcp.mmwhub.tech/mcp",
      "headers": {
        "Authorization": "Bearer <YOUR_MMW_API_KEY>"
      }
    }
  }
}
```

---

## 🛠 Available MCP Tools

| Tool | Description |
| :--- | :--- |
| `remember` | Store long-term knowledge with confidence score, source ID, hash, and provenance tags. |
| `search` | Instant (<2ms) semantic retrieval over past session decisions, facts, and constraints. |
| `validate_memory` | Validate memory consistency, verify facts, and resolve contradictory statements. |
| `forget` | Prune or mark obsolete memories as superseded. |
| `gateway_call` | Execute tenant-isolated external integrations and connected project tools. |

---

## 🚀 One-Click Setup Script

We provide automated setup scripts in this repository for macOS, Linux, and Windows:

```bash
# macOS / Linux
chmod +x connect.sh
MMW_CREDENTIAL='<YOUR_MMW_API_KEY>' ./connect.sh --client cursor --verify

# Windows (PowerShell)
$env:MMW_CREDENTIAL='<YOUR_MMW_API_KEY>'
.\connect.ps1 -Client cursor -Verify
```

---

## 🌐 Links & Resources

- **Website:** [https://mmwhub.tech](https://mmwhub.tech)
- **Web App & API Keys:** [https://app.mmwhub.tech](https://app.mmwhub.tech)
- **Smithery Registry:** [https://smithery.ai/server/mmsingatullin/mmw](https://smithery.ai/server/mmsingatullin/mmw)
- **Documentation:** [https://mmwhub.tech/docs](https://mmwhub.tech)
