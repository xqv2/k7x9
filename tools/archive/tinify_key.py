#!/usr/bin/env python3
"""Open the user's TinyPNG dashboard (they're logged in) and pull the API key
from the page so we can compress images with the official API."""

import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import opentabs

URL = "https://tinify.com/dashboard/api"


def rpc_tab(tab_id, code):
    res = opentabs.rpc("tools/call", {
        "name": "browser_execute_script",
        "arguments": {"tabId": tab_id, "code": code},
    })
    raw = res["content"][0]["text"]
    outer = json.loads(raw)
    return outer.get("value", outer)


def list_tabs():
    res = opentabs.rpc("tools/call", {"name": "browser_list_tabs", "arguments": {}})
    text = res["content"][0]["text"]
    return json.loads(text) if isinstance(text, str) else text


def main():
    tabs = list_tabs()
    tab_id = None
    for t in tabs:
        if "tinify.com" in (t.get("url") or "") and "dashboard" in (t.get("url") or ""):
            tab_id = t["id"]
            break
    if not tab_id:
        res = opentabs.rpc("tools/call", {
            "name": "browser_open_tab",
            "arguments": {"url": URL},
        })
        print("opened tab:", json.dumps(res)[:200])
        for _ in range(30):
            time.sleep(2)
            for t in list_tabs():
                if "tinify.com/dashboard" in (t.get("url") or ""):
                    tab_id = t["id"]
                    break
            if tab_id:
                break
    if not tab_id:
        raise SystemExit("could not open/find the TinyPNG dashboard tab")

    time.sleep(5)
    text = rpc_tab(tab_id, "document.body ? document.body.innerText.slice(0, 6000) : 'loading'")
    print("=== page text (first 3000) ===")
    print(text[:3000] if isinstance(text, str) else json.dumps(text)[:3000])
    print("=== search for key patterns ===")
    import re
    for pat in [r"[A-Za-z0-9]{20,}_[A-Za-z0-9]{20,}", r"[a-f0-9]{32}", r"apikey[\"':= ]+([A-Za-z0-9_\-]+)", r"key[\"':= ]+([A-Za-z0-9_\-]{20,})"]:
        m = re.findall(pat, str(text))
        if m:
            print("PATTERN", pat, "->", m[:5])


if __name__ == "__main__":
    main()
