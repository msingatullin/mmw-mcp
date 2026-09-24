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
  --client <name>    Client type: vscode | windsurf | cursor | claude | gemini | codex | generic
                     (If omitted, auto-detects based on installed environments)
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

# Client Auto-Detection if not explicitly supplied
if [[ -z "$CLIENT" ]]; then
  if [[ -d "$HOME/.cursor" ]]; then
    CLIENT="cursor"
  elif [[ -d "$HOME/.codeium/windsurf" ]]; then
    CLIENT="windsurf"
  elif [[ -d "$HOME/.vscode" || -d "$HOME/.config/Code" ]]; then
    CLIENT="vscode"
  elif [[ -d "$HOME/Library/Application Support/Claude" || -d "$HOME/.config/Claude" ]]; then
    CLIENT="claude"
  else
    CLIENT="generic"
  fi
  echo "Auto-detected IDE / agent client: $CLIENT"
fi

case "$CLIENT" in
  vscode|windsurf|cursor|claude|gemini|codex|generic) ;;
  *) echo "ERROR: Unsupported client: $CLIENT" >&2; exit 2 ;;
esac

root="$HOME/.config/mmw"
secret="$root/credential"

config_path() {
  case "$CLIENT" in
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

if [[ "$UNINSTALL" -eq 1 ]]; then
  path="$(config_path)"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[DRY-RUN] Would remove config at: $path"
    echo "[DRY-RUN] Would remove credential at: $secret"
    exit 0
  fi
  [[ -z "$path" ]] || rm -f "$path"
  rm -f "$secret"
  echo "MMW local credential and generated client config removed"
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
  echo "Target Client: $CLIENT"
  echo "Endpoint: $ENDPOINT"
  echo "Workspace: $WORKSPACE"
  path="$(config_path)"
  if [[ -n "$path" ]]; then
    echo "Target Config Path: $path"
    echo "Config Content Preview:"
    python3 - "$server_json" <<'PY'
import json
import sys
server = json.loads(sys.argv[1])
print(json.dumps({"mcpServers": {"mmw": server}}, indent=2))
PY
  elif [[ "$CLIENT" == "codex" ]]; then
    echo "Codex TOML Preview:"
    cat <<EOF
[mcp_servers.mmw]
url = "$ENDPOINT"
bearer_token_env_var = "MMW_CREDENTIAL"
EOF
  else
    echo "Raw Server JSON:"
    printf '%s\n' "$server_json"
  fi
  echo "=== END DRY-RUN (no files written) ==="
  exit 0
fi

mkdir -p "$root"
chmod 700 "$root"
printf '%s' "$credential" > "$secret"
chmod 600 "$secret"

case "$CLIENT" in
  vscode|windsurf|cursor|claude|gemini)
    path="$(config_path)"
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
    echo "MMW client config written: $path"
    ;;
  codex)
    cat <<EOF
[mcp_servers.mmw]
url = "$ENDPOINT"
bearer_token_env_var = "MMW_CREDENTIAL"
EOF
    ;;
  generic)
    printf '%s\n' "$server_json"
    ;;
esac

if [[ "$VERIFY" -eq 1 ]]; then
  echo "Verifying connection to $ENDPOINT..."
  curl -fsS -o /dev/null -X POST "$ENDPOINT" \
    -H "Authorization: Bearer $credential" \
    -H 'Content-Type: application/json' \
    -H 'Accept: application/json, text/event-stream' \
    --data '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"mmw-connect-kit","version":"1.2"}}}'
  echo "MMW MCP connection verified successfully!"
fi
