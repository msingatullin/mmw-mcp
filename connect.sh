#!/usr/bin/env bash
set -euo pipefail

ENDPOINT="${MMW_ENDPOINT:-https://mcp.mmwhub.tech/mcp}"
WORKSPACE="${MMW_WORKSPACE:-default}"
CLIENT="generic"
VERIFY=0
UNINSTALL=0

usage() {
  cat <<'EOF'
Usage: ./connect.sh [--client claude|cursor|gemini|codex|generic] [--verify] [--uninstall]

Environment:
  MMW_CREDENTIAL  MMW credential. If omitted, the script prompts securely.
  MMW_ENDPOINT    MCP endpoint. Default: https://mcp.mmwhub.tech/mcp
  MMW_WORKSPACE   Workspace label. Default: default
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --client)
      [[ $# -ge 2 ]] || { echo "--client requires a value" >&2; exit 2; }
      CLIENT="$2"; shift 2 ;;
    --verify) VERIFY=1; shift ;;
    --uninstall) UNINSTALL=1; shift ;;
    --workspace)
      [[ $# -ge 2 ]] || { echo "--workspace requires a value" >&2; exit 2; }
      WORKSPACE="$2"; shift 2 ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

case "$CLIENT" in
  claude|cursor|gemini|codex|generic) ;;
  *) echo "Unsupported client: $CLIENT" >&2; exit 2 ;;
esac

root="$HOME/.config/mmw"
secret="$root/credential"

config_path() {
  case "$CLIENT" in
    claude) printf '%s' "$HOME/Library/Application Support/Claude/claude_desktop_config.json" ;;
    cursor) printf '%s' "$HOME/.cursor/mcp.json" ;;
    gemini) printf '%s' "$HOME/.gemini/mmw-mcp.json" ;;
    *) printf '' ;;
  esac
}

if [[ "$UNINSTALL" -eq 1 ]]; then
  path="$(config_path)"
  [[ -z "$path" ]] || rm -f "$path"
  rm -f "$secret"
  echo "MMW local credential and generated client config removed"
  exit 0
fi

credential="${MMW_CREDENTIAL:-}"
if [[ -z "$credential" && -s "$secret" ]]; then
  credential="$(<"$secret")"
fi
if [[ -z "$credential" ]]; then
  read -r -s -p "MMW credential: " credential
  printf '\n' >&2
fi
[[ -n "$credential" ]] || { echo "MMW credential is required" >&2; exit 2; }

mkdir -p "$root"
chmod 700 "$root"
printf '%s' "$credential" > "$secret"
chmod 600 "$secret"

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

case "$CLIENT" in
  claude|cursor|gemini)
    path="$(config_path)"
    mkdir -p "$(dirname "$path")"
    python3 - "$path" "$server_json" <<'PY'
import json
import os
import sys

path = sys.argv[1]
server = json.loads(sys.argv[2])
with open(path, "w", encoding="utf-8") as handle:
    json.dump({"mcpServers": {"mmw": server}}, handle, indent=2)
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
  curl -fsS -o /dev/null -X POST "$ENDPOINT" \
    -H "Authorization: Bearer $credential" \
    -H 'Content-Type: application/json' \
    -H 'Accept: application/json, text/event-stream' \
    --data '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"mmw-connect-kit","version":"1.0"}}}'
  echo "MMW MCP connection verified"
fi
