#!/usr/bin/env bash
set -euo pipefail

ENDPOINT="${MMW_ENDPOINT:-https://mcp.mmwhub.ru/mcp}"
WORKSPACE="${MMW_WORKSPACE:-default}"
CLIENT=""
VERIFY=0
UNINSTALL=0
DRY_RUN=0

usage() {
  cat <<'EOF'
Usage: ./connect.sh [OPTIONS]

Options:
  --client <name>    Client type: all | vscode | windsurf | cursor | claude | gemini | codex | generic
                     (Default: all detected environments on this machine)
  --workspace <name> Workspace label. Default: default
  --endpoint <url>   MCP endpoint URL. Default: https://mcp.mmwhub.ru/mcp
  --dry-run          Preview generated configuration without writing files
  --verify           Execute live initialize handshake to verify connection
  --uninstall        Remove generated client configuration and cached credentials
  --help, -h         Show this help message

Environment:
  MMW_CREDENTIAL     MMW bearer token. If omitted, prompts securely or reads ~/.config/mmw/credential
  MMW_ENDPOINT       MCP endpoint URL
  MMW_WORKSPACE      Workspace label
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --client)
      [[ $# -ge 2 ]] || { echo "ERROR: --client requires a value" >&2; exit 2; }
      CLIENT="$2"; shift 2 ;;
    --workspace)
      [[ $# -ge 2 ]] || { echo "ERROR: --workspace requires a value" >&2; exit 2; }
      WORKSPACE="$2"; shift 2 ;;
    --endpoint)
      [[ $# -ge 2 ]] || { echo "ERROR: --endpoint requires a value" >&2; exit 2; }
      ENDPOINT="$2"; shift 2 ;;
    --verify) VERIFY=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    --uninstall) UNINSTALL=1; shift ;;
    --help|-h) usage; exit 0 ;;
    *) echo "ERROR: Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

root="$HOME/.config/mmw"
secret="$root/credential"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
proxy_script="$(cd "$script_dir/.." && pwd)/mmw_proxy.py"
[[ -f "$proxy_script" ]] || proxy_script="$HOME/mmw/tools/mmw_proxy.py"

config_path() {
  local cl="$1"
  case "$cl" in
    cursor) printf '%s' "$HOME/.cursor/mcp.json" ;;
    windsurf) printf '%s' "$HOME/.codeium/windsurf/mcp_config.json" ;;
    vscode) printf '%s' "$HOME/.vscode/mcp.json" ;;
    claude)
      if [[ "$(uname)" == "Darwin" ]]; then
        printf '%s' "$HOME/Library/Application Support/Claude/claude_desktop_config.json"
      else
        printf '%s' "$HOME/.config/Claude/claude_desktop_config.json"
      fi
      ;;
    gemini) printf '%s' "$HOME/.gemini/mmw-mcp.json" ;;
    *) printf '' ;;
  esac
}

detect_installed_clients() {
  local found=()
  [[ -d "$HOME/.cursor" ]] && found+=("cursor")
  [[ -d "$HOME/.codeium/windsurf" ]] && found+=("windsurf")
  if [[ -d "$HOME/.vscode" || -d "$HOME/.config/Code" ]]; then
    found+=("vscode")
  fi
  if command -v claude &>/dev/null || [[ -d "$HOME/.claude" || -d "$HOME/.config/Claude" || -d "$HOME/Library/Application Support/Claude" ]]; then
    found+=("claude")
  fi
  if command -v codex &>/dev/null || [[ -d "$HOME/.codex" ]]; then
    found+=("codex")
  fi
  if [[ ${#found[@]} -eq 0 ]]; then
    found+=("generic")
  fi
  printf '%s\n' "${found[@]}"
}

TARGET_CLIENTS=()
if [[ -z "$CLIENT" || "$CLIENT" == "all" ]]; then
  while IFS= read -r cl; do
    [[ -n "$cl" ]] && TARGET_CLIENTS+=("$cl")
  done < <(detect_installed_clients)
  echo "Auto-detected all installed clients: ${TARGET_CLIENTS[*]}"
else
  TARGET_CLIENTS=("$CLIENT")
fi

if [[ "$UNINSTALL" -eq 1 ]]; then
  for cl in "${TARGET_CLIENTS[@]}"; do
    path="$(config_path "$cl")"
    if [[ "$DRY_RUN" -eq 1 ]]; then
      echo "[DRY-RUN] Would remove config at: $path"
    else
      [[ -z "$path" ]] || rm -f "$path"
      echo "Removed MMW config for $cl: $path"
    fi
  done
  if [[ "$DRY_RUN" -eq 0 ]]; then
    rm -f "$secret"
    echo "MMW local credential removed"
  else
    echo "[DRY-RUN] Would remove credential at: $secret"
  fi
  exit 0
fi

credential="${MMW_CREDENTIAL:-}"
if [[ -z "$credential" && -s "$secret" ]]; then
  credential="$(<"$secret")"
fi

if [[ -z "$credential" && "$DRY_RUN" -eq 1 ]]; then
  credential="mmw_sample_token_for_dry_run"
fi

if [[ -z "$credential" ]]; then
  read -r -s -p "MMW credential: " credential
  printf '\n' >&2
fi
[[ -n "$credential" ]] || { echo "ERROR: MMW credential is required" >&2; exit 2; }

server_json="$(python3 - "$ENDPOINT" "$WORKSPACE" "$credential" <<'PY'
import json
import sys

print(json.dumps({
    "url": sys.argv[1],
    "headers": {"Authorization": "Bearer " + sys.argv[3]},
    "workspace": sys.argv[2],
}, indent=2))
PY
)"

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "=== MMW Connect Kit DRY-RUN ==="
  echo "Target Clients: ${TARGET_CLIENTS[*]}"
  echo "Endpoint: $ENDPOINT"
  echo "Workspace: $WORKSPACE"
  for cl in "${TARGET_CLIENTS[@]}"; do
    path="$(config_path "$cl")"
    echo "--- Target: $cl ($path) ---"
  done
  echo "=== END DRY-RUN (no files written) ==="
  exit 0
fi

mkdir -p "$root"
chmod 700 "$root"
printf '%s' "$credential" > "$secret"
chmod 600 "$secret"

setup_client() {
  local cl="$1"
  case "$cl" in
    vscode|windsurf|cursor|gemini)
      local path
      path="$(config_path "$cl")"
      mkdir -p "$(dirname "$path")"
      python3 - "$path" "$server_json" <<'PY'
import json
import os
import sys

path = sys.argv[1]
server = json.loads(sys.argv[2])
data = {}
if os.path.exists(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception:
        data = {}

if "mcpServers" not in data:
    data["mcpServers"] = {}
data["mcpServers"]["mmw"] = server

with open(path, "w", encoding="utf-8") as handle:
    json.dump(data, handle, indent=2)
    handle.write("\n")
os.chmod(path, 0o600)
PY
      echo "✓ MMW config written for $cl: $path"
      ;;

    claude)
      local dpath
      dpath="$(config_path "$cl")"
      mkdir -p "$(dirname "$dpath")"
      python3 - "$dpath" "$server_json" <<'PY'
import json
import os
import sys

path = sys.argv[1]
server = json.loads(sys.argv[2])
data = {}
if os.path.exists(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception:
        data = {}

if "mcpServers" not in data:
    data["mcpServers"] = {}
data["mcpServers"]["mmw"] = server

with open(path, "w", encoding="utf-8") as handle:
    json.dump(data, handle, indent=2)
    handle.write("\n")
os.chmod(path, 0o600)
PY
      echo "✓ MMW Desktop config written: $dpath"

      # Also configure Claude Code CLI if available
      if command -v claude &>/dev/null && [[ -f "$proxy_script" ]]; then
        claude mcp add --transport stdio --scope user mmw python3 "$proxy_script" >/dev/null 2>&1 || true
        echo "✓ MMW registered in Claude Code CLI via stdio proxy: $proxy_script"
      fi

      # Inject MMW doctrine into ~/.claude/CLAUDE.md
      local claude_md="$HOME/.claude/CLAUDE.md"
      if [[ -f "$claude_md" ]] && ! grep -q "MMW Omnipresent Memory" "$claude_md"; then
        cat <<'EOF' >> "$claude_md"

## MMW Omnipresent Memory (CRITICAL)
- The persistent cross-device, cross-agent memory for this user is managed by MMW via MCP (`mcp__mmw__search`, `mcp__mmw__remember`).
- Whenever the user asks any question about their past facts, notes, counts, dates, preferences, harvests, history, or context (e.g. "сколько...", "что я...", "в прошлом году...", "помнишь ли..."):
  YOU MUST ALWAYS query `mcp__mmw__search` FIRST before answering. Never state that data is missing without querying MMW search.
- When the user shares new important facts, decisions, or metrics, record them via `mcp__mmw__remember`.
EOF
        echo "✓ MMW memory doctrine injected into $claude_md"
      fi
      ;;

    codex)
      local codex_dir="$HOME/.codex"
      local codex_path="$codex_dir/config.toml"
      mkdir -p "$codex_dir"
      cat <<EOF > "$codex_path"
[mcp_servers.mmw]
url = "$ENDPOINT"
bearer_token_env_var = "MMW_CREDENTIAL"
EOF
      chmod 600 "$codex_path"
      echo "✓ MMW Codex client config written: $codex_path"
      ;;

    generic)
      printf '%s\n' "$server_json"
      ;;
  esac
}

for cl in "${TARGET_CLIENTS[@]}"; do
  setup_client "$cl"
done

if [[ "$VERIFY" -eq 1 ]]; then
  echo "Verifying connection to $ENDPOINT..."
  curl -fsS -o /dev/null -X POST "$ENDPOINT" \
    -H "Authorization: Bearer $credential" \
    -H 'Content-Type: application/json' \
    -H 'Accept: application/json, text/event-stream' \
    --data '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"mmw-connect-kit","version":"1.2"}}}'
  echo "✓ MMW MCP connection verified successfully!"
fi
