#!/usr/bin/env python3
"""
MMW Local-First Resilient MCP Proxy & Offline Spooler.

Features:
1. Local SQLite spool database: ~/.mmw/spool.db
2. Ultra-low latency (<1ms): remember() is written locally immediately, returns success to LLM.
3. Background synchronization: Asynchronously flushes spool queue to remote MMW cloud.
4. Seamless fallback: If offline / network error / auth token expired, queue retains items with exponential backoff.
5. Unified search(): Merges remote cloud results with un-synced local spool items.
6. Standard stdio transport: Compatible with Claude Desktop, Cursor, VS Code, Windsurf.
"""

import sys
import os
import json
import sqlite3
import datetime
import urllib.request
import urllib.error
import threading
import time

SPOOL_DIR = os.path.expanduser("~/.config/mmw")
SPOOL_DB = os.path.join(SPOOL_DIR, "spool.db")
DEFAULT_ENDPOINT = os.environ.get("MMW_ENDPOINT", "https://mcp.mmwhub.tech/mcp")
DEFAULT_WORKSPACE = os.environ.get("MMW_WORKSPACE", "default")
CREDENTIAL_FILE = os.path.join(SPOOL_DIR, "credential")

def get_token():
    token = os.environ.get("MMW_TOKEN") or os.environ.get("MMW_CREDENTIAL")
    if not token and os.path.exists(CREDENTIAL_FILE):
        try:
            with open(CREDENTIAL_FILE, "r") as f:
                token = f.read().strip()
        except Exception:
            pass
    return token or ""

def init_spool():
    os.makedirs(SPOOL_DIR, exist_ok=True)
    conn = sqlite3.connect(SPOOL_DB)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS spool_queue (
            id TEXT PRIMARY KEY,
            workspace TEXT NOT NULL,
            scope TEXT NOT NULL,
            title TEXT,
            content TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending', -- pending, synced, failed
            retry_count INTEGER NOT NULL DEFAULT 0,
            last_error TEXT,
            created_at TEXT NOT NULL,
            synced_at TEXT
        );
    """)
    conn.commit()
    conn.close()

def spool_remember(workspace: str, scope: str, title: str, content: str) -> str:
    init_spool()
    item_id = f"local-spool-{int(time.time()*1000)}-{os.urandom(4).hex()}"
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    conn = sqlite3.connect(SPOOL_DB)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO spool_queue (id, workspace, scope, title, content, status, retry_count, created_at)
        VALUES (?, ?, ?, ?, ?, 'pending', 0, ?)
    """, (item_id, workspace, scope, title, content, now))
    conn.commit()
    conn.close()
    return item_id

def sync_worker():
    """Background worker that drains pending items from spool.db to remote MMW endpoint."""
    while True:
        try:
            token = get_token()
            if not token:
                time.sleep(5)
                continue

            init_spool()
            conn = sqlite3.connect(SPOOL_DB)
            cur = conn.cursor()
            cur.execute("""
                SELECT id, workspace, scope, title, content, retry_count
                FROM spool_queue
                WHERE status = 'pending'
                ORDER BY created_at ASC
                LIMIT 5
            """)
            rows = cur.fetchall()
            conn.close()

            if not rows:
                time.sleep(3)
                continue

            for item_id, ws, scope, title, content, retries in rows:
                payload = {
                    "jsonrpc": "2.0",
                    "id": f"sync-{item_id}",
                    "method": "tools/call",
                    "params": {
                        "name": "remember",
                        "arguments": {
                            "workspace": ws,
                            "scope": scope,
                            "title": title or "",
                            "content": content
                        }
                    }
                }
                req = urllib.request.Request(
                    DEFAULT_ENDPOINT,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "Authorization": f"Bearer {token}"
                    },
                    data=json.dumps(payload).encode("utf-8")
                )
                try:
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        res_data = json.loads(resp.read().decode("utf-8"))
                        if "error" not in res_data:
                            # Mark synced
                            conn = sqlite3.connect(SPOOL_DB)
                            cur = conn.cursor()
                            now = datetime.datetime.now(datetime.timezone.utc).isoformat()
                            cur.execute("""
                                UPDATE spool_queue
                                SET status = 'synced', synced_at = ?
                                WHERE id = ?
                            """, (now, item_id))
                            conn.commit()
                            conn.close()
                        else:
                            raise Exception(res_data.get("error"))
                except Exception as ex:
                    # Update retry count and error
                    conn = sqlite3.connect(SPOOL_DB)
                    cur = conn.cursor()
                    cur.execute("""
                        UPDATE spool_queue
                        SET retry_count = retry_count + 1, last_error = ?
                        WHERE id = ?
                    """, (str(ex), item_id))
                    conn.commit()
                    conn.close()
                    # Backoff on error
                    time.sleep(min(30, 2 ** retries))

            time.sleep(2)
        except Exception:
            time.sleep(5)

def call_remote(method: str, params: dict):
    token = get_token()
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params
    }
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(
        DEFAULT_ENDPOINT,
        headers=headers,
        data=json.dumps(payload).encode("utf-8")
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))

def handle_request(req: dict) -> dict:
    method = req.get("method")
    req_id = req.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {"listChanged": False}
                },
                "serverInfo": {
                    "name": "MMW Local-First Resilient MCP Proxy",
                    "version": "1.1.0"
                },
                "instructions": "MMW Local-First Memory: All writes are spooled locally first for 100% offline resilience and synchronized with MMW cloud."
            }
        }

    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": [
                    {
                        "name": "remember",
                        "description": "Store a persistent memory fact or architectural decision. Guaranteed local spooling with background cloud sync.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "content": {"type": "string", "description": "The exact fact, decision or context to remember"},
                                "title": {"type": "string", "description": "Short title or key concept"},
                                "scope": {"type": "string", "description": "Scope of memory (project, system, agent)", "default": "project"},
                                "workspace": {"type": "string", "description": "Target workspace", "default": DEFAULT_WORKSPACE}
                            },
                            "required": ["content"]
                        }
                    },
                    {
                        "name": "search",
                        "description": "Search memories across both local spool and remote MMW cloud.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string", "description": "Natural language search query"},
                                "workspace": {"type": "string", "description": "Target workspace", "default": DEFAULT_WORKSPACE}
                            },
                            "required": ["query"]
                        }
                    },
                    {
                        "name": "spool_status",
                        "description": "Inspect the status of the local offline spool queue and sync state.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {}
                        }
                    }
                ]
            }
        }

    elif method == "tools/call":
        params = req.get("params", {})
        tool_name = params.get("name")
        args = params.get("arguments", {})

        if tool_name == "remember":
            content = args.get("content", "")
            title = args.get("title", "")
            scope = args.get("scope", "project")
            workspace = args.get("workspace", DEFAULT_WORKSPACE)

            spool_id = spool_remember(workspace, scope, title, content)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": f"✓ Memory saved to local resilient spool ({spool_id}). Queued for cloud sync."
                        }
                    ]
                }
            }

        elif tool_name == "spool_status":
            init_spool()
            conn = sqlite3.connect(SPOOL_DB)
            cur = conn.cursor()
            cur.execute("SELECT status, count(*) FROM spool_queue GROUP BY status")
            counts = dict(cur.fetchall())
            cur.execute("SELECT id, title, status, retry_count, last_error, created_at FROM spool_queue ORDER BY created_at DESC LIMIT 5")
            recent = [
                {"id": r[0], "title": r[1], "status": r[2], "retries": r[3], "error": r[4], "created": r[5]}
                for r in cur.fetchall()
            ]
            conn.close()
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps({"queue_summary": counts, "recent_items": recent}, indent=2)
                        }
                    ]
                }
            }

        elif tool_name == "search":
            query = args.get("query", "").lower()
            # 1. Search local pending spool
            init_spool()
            conn = sqlite3.connect(SPOOL_DB)
            cur = conn.cursor()
            cur.execute("""
                SELECT id, title, content, created_at, status
                FROM spool_queue
                WHERE (lower(content) LIKE ? OR lower(title) LIKE ?)
                ORDER BY created_at DESC
                LIMIT 10
            """, (f"%{query}%", f"%{query}%"))
            local_matches = [
                {"id": r[0], "title": r[1], "content": r[2], "source": f"local_spool ({r[4]})", "created_at": r[3]}
                for r in cur.fetchall()
            ]
            conn.close()

            # 2. Search remote cloud
            remote_matches = []
            try:
                remote_res = call_remote("tools/call", {
                    "name": "search",
                    "arguments": args
                })
                if "result" in remote_res and "content" in remote_res["result"]:
                    remote_matches.append(remote_res["result"]["content"][0]["text"])
            except Exception as e:
                remote_matches.append(f"[Remote cloud offline or unauthenticated: {e}]")

            combined_output = {
                "query": query,
                "local_spool_hits": local_matches,
                "remote_cloud_hits": remote_matches
            }
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(combined_output, indent=2, ensure_ascii=False)
                        }
                    ]
                }
            }

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Method {method} not found"}
    }

def main():
    # Start background sync thread
    worker = threading.Thread(target=sync_worker, daemon=True)
    worker.start()

    # Process stdin line by line (JSON-RPC over stdio)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            res = handle_request(req)
            sys.stdout.write(json.dumps(res) + "\n")
            sys.stdout.flush()
        except Exception as e:
            err_res = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": str(e)}
            }
            sys.stdout.write(json.dumps(err_res) + "\n")
            sys.stdout.flush()

if __name__ == "__main__":
    main()
