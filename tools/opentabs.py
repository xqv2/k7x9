#!/usr/bin/env python3
"""
MCP-over-HTTP (streamable) client for the local OpenTabs server.

Persists one session in tools/.opentabs-session (session id travels in the
response header) and reuses it, so the server's 5-sessions/min rate limit
is never tripped.

Usage:
    python3 tools/opentabs.py tools/list
    python3 tools/opentabs.py tools/call browser_list_tabs '{}'
    python3 tools/opentabs.py tools/call browser_open_tab '{"url": "https://..."}'
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request

def load_secret():
    """OpenTabs MCP server auth secret — env var first, else the server's own
    auth.json (same file the local server and Chrome extension use)."""
    env = os.environ.get("OPENTABS_SECRET")
    if env:
        return env
    for p in (os.path.expanduser("~/.opentabs/extension/auth.json"),
              os.path.expanduser("~/.opentabs/auth.json")):
        try:
            with open(p) as f:
                return json.load(f)["secret"]
        except (OSError, KeyError, json.JSONDecodeError):
            continue
    raise SystemExit("OpenTabs secret not found — set OPENTABS_SECRET or check ~/.opentabs/extension/auth.json")


SECRET = load_secret()
URL = "http://127.0.0.1:9515/mcp"
SESSION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".opentabs-session")


def gethdr(headers, name):
    for k, v in headers.items():
        if k.lower() == name.lower():
            return v
    return None


def _post(body, sess=None):
    h = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "Authorization": f"Bearer {SECRET}",
    }
    if sess:
        h["Mcp-Session-Id"] = sess
    req = urllib.request.Request(URL, data=json.dumps(body).encode(), headers=h, method="POST")
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return r.status, r.headers, r.read().decode()
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(65)
                continue
            return e.code, e.headers, e.read().decode()
    return 429, {}, "rate limited"


def parse_sse(raw):
    out = []
    for line in raw.splitlines():
        if line.startswith("data: "):
            try:
                out.append(json.loads(line[6:]))
            except json.JSONDecodeError:
                pass
    return out


def _load_session():
    try:
        with open(SESSION_FILE) as f:
            return f.read().strip() or None
    except OSError:
        return None


def _save_session(sess):
    with open(SESSION_FILE, "w") as f:
        f.write(sess or "")


def ensure_session():
    """Return a session id. Re-init only when the stored one goes stale."""
    sess = _load_session()
    if sess:
        return sess
    status, hdrs, raw = _post({
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "codebuff", "version": "1.0"},
        },
    })
    sess = gethdr(hdrs, "Mcp-Session-Id")
    _save_session(sess)
    if sess:
        _post({"jsonrpc": "2.0", "method": "notifications/initialized"}, sess=sess)
        time.sleep(0.5)  # let the server register the transport
    return sess


def rpc(method, params=None):
    sess = ensure_session()
    body = {"jsonrpc": "2.0", "id": 1, "method": method}
    if params is not None:
        body["params"] = params
    status, hdrs, raw = _post(body, sess=sess)
    if status != 200:
        if status in (404, 400) and method == "tools/call":
            # stale session — retry once with a fresh one
            os.remove(SESSION_FILE)
            sess = ensure_session()
            status, hdrs, raw = _post(body, sess=sess)
        else:
            raise RuntimeError(f"HTTP {status}: {raw[:300]}")
    msgs = parse_sse(raw)
    if not msgs:
        raise RuntimeError(f"empty response ({status})")
    result = msgs[-1].get("result")
    if result is None and msgs[-1].get("error"):
        raise RuntimeError(json.dumps(msgs[-1]["error"]))
    return result


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return
    if args[0] == "tools/list":
        for t in (rpc("tools/list") or {}).get("tools", []):
            print(t["name"])
            desc = (t.get("description") or "").split("\n")[0]
            if desc:
                print(f"    {desc[:110]}")
        return
    if args[0] == "tools/call" and len(args) >= 3:
        name, params = args[1], json.loads(args[2])
        print(json.dumps(rpc("tools/call", {"name": name, "arguments": params}), indent=2)[:12000])
        return
    print("unknown command", file=sys.stderr)


if __name__ == "__main__":
    main()
