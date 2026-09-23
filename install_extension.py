#!/usr/bin/env python3
"""
MMW One-Click Desktop Extension Installer (.mcpb handler)
Installs MMW Managed Memory Workspace into Claude Desktop, Cursor, and Windsurf configurations.
"""
import os
import sys
import json
from pathlib import Path

ENDPOINT = "https://mcp.mmwhub.tech/mcp"

def get_token():
    token = os.environ.get("MMW_API_KEY") or os.environ.get("MMW_TOKEN")
    if not token and len(sys.argv) > 1:
        token = sys.argv[1]
    return token

def install_claude(token):
    paths = [
        Path.home() / "Library/Application Support/Claude/claude_desktop_config.json",
        Path.home() / ".config/Claude/claude_desktop_config.json",
        Path(os.environ.get("APPDATA", "")) / "Claude/claude_desktop_config.json"
    ]
    installed = False
    for p in paths:
        if p.parent.exists():
            data = {}
            if p.exists():
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception:
                    data = {}
            data.setdefault("mcpServers", {})
            data["mcpServers"]["mmw"] = {
                "url": ENDPOINT,
                "headers": {"Authorization": f"Bearer {token}" if token else "Bearer YOUR_TOKEN"}
            }
            with open(p, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            print(f"[✓] Installed to Claude Desktop: {p}")
            installed = True
    return installed

def install_cursor(token):
    p = Path.home() / ".cursor/mcp.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    data = {}
    if p.exists():
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
    data.setdefault("mcpServers", {})
    data["mcpServers"]["mmw"] = {
        "url": ENDPOINT,
        "headers": {"Authorization": f"Bearer {token}" if token else "Bearer YOUR_TOKEN"}
    }
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"[✓] Installed to Cursor: {p}")

def main():
    token = get_token()
    print("==============================================")
    print("  MMW One-Click Desktop Extension (.mcpb)     ")
    print("==============================================")
    install_claude(token)
    install_cursor(token)
    print("[✓] Zero-touch installation complete!")

if __name__ == "__main__":
    main()
