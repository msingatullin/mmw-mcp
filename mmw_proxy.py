#!/usr/bin/env python3
"""
MMW Local-First Resilient MCP Proxy & Offline Spooler (v1.2.0)

Features:
1. Local SQLite spool database: ~/.config/mmw/spool.db
2. Ultra-low latency (<1ms): remember() and forget() written locally immediately, returns success.
3. Background synchronization: Asynchronously flushes spool queue to remote MMW cloud with exponential backoff.
4. Deterministic Idempotency: Generates and attaches X-Idempotency-Key (SHA256 of canonical payload) on all mutations.
5. Session Resumption: Manages mcp-session-id across requests and automatically reconnects on expiration.
6. Graceful 401/403 Handling: Detects auth issues, pauses retry churn, and preserves pending items safely.
7. Unified search(): Merges remote cloud results with un-synced local spool items.
8. Standard stdio transport: Compatible with Cursor, VS Code, Windsurf, Claude Desktop, and GigaAgent.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import sqlite3
import sys
import threading
import time
import urllib.error
import urllib.request

SPOOL_DIR = os.path.expanduser("~/.config/mmw")
SPOOL_DB = os.path.join(SPOOL_DIR, "spool.db")
DEFAULT_ENDPOINT = os.environ.get("MMW_ENDPOINT", "https://mcp.mmwhub.ru/mcp")
DEFAULT_WORKSPACE = os.environ.get("MMW_WORKSPACE", "default")
CREDENTIAL_FILE = os.path.join(SPOOL_DIR, "credential")

# Global session cache
SESSION_CACHE = {
    "session_id": None,
    "last_init": 0.0,
    "lock": threading.Lock()
}


def get_token() -> str:
    token = os.environ.get("MMW_TOKEN") or os.environ.get("MMW_CREDENTIAL")
    if not token and os.path.exists(CREDENTIAL_FILE):
        try:
            with open(CREDENTIAL_FILE, "r", encoding="utf-8") as f:
                token = f.read().strip()
        except Exception:
            pass
    return token or ""


def compute_idempotency_key(data: dict) -> str:
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def init_spool() -> None:
    os.makedirs(SPOOL_DIR, exist_ok=True)
    conn = sqlite3.connect(SPOOL_DB)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS spool_queue (
            id TEXT PRIMARY KEY,
            action TEXT NOT NULL DEFAULT 'remember', -- remember, forget
            workspace TEXT NOT NULL,
            scope TEXT NOT NULL,
            title TEXT,
            content TEXT NOT NULL,
            idempotency_key TEXT,
            status TEXT NOT NULL DEFAULT 'pending', -- pending, synced, failed
            retry_count INTEGER NOT NULL DEFAULT 0,
            last_error TEXT,
            created_at TEXT NOT NULL,
            synced_at TEXT
        );
    """)
    # Migration: add action or idempotency_key if upgrading existing db
    try:
        cur.execute("ALTER TABLE spool_queue ADD COLUMN action TEXT NOT NULL DEFAULT 'remember'")
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE spool_queue ADD COLUMN idempotency_key TEXT")
    except Exception:
        pass
    conn.commit()
    conn.close()


def spool_mutation(action: str, workspace: str, scope: str, title: str, content: str) -> tuple[str, str]:
    init_spool()
    item_id = f"local-spool-{int(time.time()*1000)}-{os.urandom(4).hex()}"
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    canonical_payload = {
        "action": action,
        "workspace": workspace,
        "scope": scope,
        "title": title,
        "content": content
    }
    idem_key = compute_idempotency_key(canonical_payload)

    conn = sqlite3.connect(SPOOL_DB)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO spool_queue (id, action, workspace, scope, title, content, idempotency_key, status, retry_count, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', 0, ?)
    """, (item_id, action, workspace, scope, title, content, idem_key, now))
    conn.commit()
    conn.close()
    return item_id, idem_key


def get_or_create_session(token: str, force_refresh: bool = False) -> str | None:
    with SESSION_CACHE["lock"]:
        now = time.time()
        if not force_refresh and SESSION_CACHE["session_id"] and (now - SESSION_CACHE["last_init"] < 300):
            return SESSION_CACHE["session_id"]

        init_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "mmw-resilient-proxy", "version": "1.2.0"}
            }
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        req = urllib.request.Request(DEFAULT_ENDPOINT, data=json.dumps(init_payload).encode("utf-8"), headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                sid = resp.headers.get("mcp-session-id")
                if not sid:
                    body = json.loads(resp.read().decode("utf-8"))
                    sid = body.get("result", {}).get("sessionId")
                SESSION_CACHE["session_id"] = sid
                SESSION_CACHE["last_init"] = now
                return sid
        except Exception:
            return None


def call_remote(method: str, params: dict, is_mutation: bool = False, idempotency_key: str | None = None) -> dict:
    token = get_token()
    session_id = get_or_create_session(token)

    payload = {
        "jsonrpc": "2.0",
        "id": int(time.time() * 1000) % 100000,
        "method": method,
        "params": params
    }
    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream"
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if session_id:
        headers["mcp-session-id"] = session_id
    if is_mutation:
        if not idempotency_key:
            idempotency_key = hashlib.sha256(data).hexdigest()
        headers["X-Idempotency-Key"] = idempotency_key

    req = urllib.request.Request(DEFAULT_ENDPOINT, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code in (400, 404):
            # Session expired, re-handshake and retry once
            session_id = get_or_create_session(token, force_refresh=True)
            if session_id:
                headers["mcp-session-id"] = session_id
            req2 = urllib.request.Request(DEFAULT_ENDPOINT, data=data, headers=headers)
            with urllib.request.urlopen(req2, timeout=12) as resp2:
                return json.loads(resp2.read().decode("utf-8"))
        elif e.code in (401, 403):
            raise PermissionError(f"HTTP {e.code}: Authentication or tenant access denied ({e.reason})")
        raise


def sync_worker() -> None:
    """Background worker draining pending local items to remote cloud."""
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
                SELECT id, action, workspace, scope, title, content, idempotency_key, retry_count
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

            for item_id, action, ws, scope, title, content, idem_key, retries in rows:
                if action == "forget":
                    call_params = {
                        "name": "forget",
                        "arguments": {"id": content}
                    }
                else:
                    call_params = {
                        "name": "remember",
                        "arguments": {
                            "workspace": ws,
                            "scope": scope,
                            "title": title or "",
                            "content": content
                        }
                    }

                try:
                    res_data = call_remote("tools/call", call_params, is_mutation=True, idempotency_key=idem_key)
                    if "error" not in res_data:
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
                except PermissionError as pe:
                    # 401/403: Stop spamming remote, wait for user intervention
                    conn = sqlite3.connect(SPOOL_DB)
                    cur = conn.cursor()
                    cur.execute("""
                        UPDATE spool_queue
                        SET retry_count = retry_count + 1, last_error = ?
                        WHERE id = ?
                    """, (str(pe), item_id))
                    conn.commit()
                    conn.close()
                    time.sleep(30)
                except Exception as ex:
                    conn = sqlite3.connect(SPOOL_DB)
                    cur = conn.cursor()
                    cur.execute("""
                        UPDATE spool_queue
                        SET retry_count = retry_count + 1, last_error = ?
                        WHERE id = ?
                    """, (str(ex), item_id))
                    conn.commit()
                    conn.close()
                    time.sleep(min(30, 2 ** min(retries, 5)))

            time.sleep(2)
        except Exception:
            time.sleep(5)


def handle_request(req: dict) -> dict:
    method = req.get("method")
    req_id = req.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2025-03-26",
                "capabilities": {
                    "tools": {"listChanged": False}
                },
                "serverInfo": {
                    "name": "MMW Local-First Resilient MCP Proxy",
                    "version": "1.2.0"
                },
                "instructions": "MMW Local-First Memory: Writes are spooled locally with zero-loss guarantee and flushed to Cloud.ru sovereign core."
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
                        "description": "Store a persistent memory fact or architectural decision with deterministic idempotency.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "content": {"type": "string", "description": "Fact or context to remember"},
                                "title": {"type": "string", "description": "Short title or topic"},
                                "scope": {"type": "string", "description": "Scope (project, shared, private)", "default": "shared"},
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
                                "workspace": {"type": "string", "description": "Target workspace", "default": DEFAULT_WORKSPACE},
                                "limit": {"type": "integer", "description": "Result limit", "default": 10}
                            },
                            "required": ["query"]
                        }
                    },
                    {
                        "name": "forget",
                        "description": "Delete a memory fact by its ID.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string", "description": "Memory atom ID to delete"}
                            },
                            "required": ["id"]
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
            scope = args.get("scope", "shared")
            workspace = args.get("workspace", DEFAULT_WORKSPACE)

            spool_id, idem_key = spool_mutation("remember", workspace, scope, title, content)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": f"✓ Memory saved to local resilient spool ({spool_id}). Idempotency key: {idem_key[:12]}... Queued for sync."
                        }
                    ],
                    "id": spool_id,
                    "idempotency_key": idem_key,
                    "status": "spooled"
                }
            }

        elif tool_name == "forget":
            atom_id = args.get("id", "")
            spool_id, idem_key = spool_mutation("forget", DEFAULT_WORKSPACE, "shared", "", atom_id)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": f"✓ Memory deletion spooled ({spool_id}) for atom {atom_id}."
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
            cur.execute("SELECT id, action, title, status, retry_count, last_error, created_at FROM spool_queue ORDER BY created_at DESC LIMIT 5")
            recent = [
                {"id": r[0], "action": r[1], "title": r[2], "status": r[3], "retries": r[4], "error": r[5], "created": r[6]}
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

            remote_matches = []
            try:
                remote_res = call_remote("tools/call", {
                    "name": "search",
                    "arguments": args
                })
                if "result" in remote_res and "content" in remote_res["result"]:
                    remote_matches.append(remote_res["result"]["content"][0]["text"])
            except PermissionError as pe:
                remote_matches.append(f"[Remote cloud auth error: {pe}]")
            except Exception as e:
                remote_matches.append(f"[Remote cloud offline or unreachable: {e}]")

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
    worker = threading.Thread(target=sync_worker, daemon=True)
    worker.start()

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
