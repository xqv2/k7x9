#!/usr/bin/env python3
"""Compress the new-batch master PNGs (build_staging.DONE | CUT_QUEUE) with
the official TinyPNG API (key in tools/.tinify-key, gitignored).

Each file: POST to https://api.tinify.com/shrink, then GET the Location URL,
and save the optimized PNG over the master. Skips already-compressed files
(tools/.tinify-progress.json). Prints before/after sizes per file.

Usage:
    python3 tools/tinify_compress.py
"""

import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
import build_staging  # noqa: E402

API = "https://api.tinify.com/shrink"
KEY_FILE = os.path.join(TOOLS, ".tinify-key")
PROGRESS = os.path.join(TOOLS, ".tinify-progress.json")
ROOT = os.path.normpath(os.path.join(TOOLS, ".."))


def key():
    with open(KEY_FILE) as f:
        return f.read().strip()


def load_progress():
    if os.path.exists(PROGRESS):
        with open(PROGRESS) as f:
            return json.load(f)
    return {}


def save_progress(p):
    with open(PROGRESS, "w") as f:
        json.dump(p, f, indent=1)


def http(url, method="GET", body=None, auth=None, retries=3):
    h = {}
    if body is not None:
        h["Content-Type"] = "application/octet-stream"
        h["Content-Length"] = str(len(body))
    if auth:
        h["Authorization"] = "Basic " + base64.b64encode(auth.encode()).decode()
    req = urllib.request.Request(url, data=body, headers=h, method=method)
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return r.status, dict(r.headers), r.read()
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                time.sleep(30)
                continue
            raise
    raise RuntimeError("request failed")


def compress(path, auth):
    with open(path, "rb") as f:
        data = f.read()
    status, hdrs, _ = http(API, "POST", body=data, auth=auth)
    loc = hdrs.get("Location")
    if not loc:
        raise RuntimeError(f"no Location header ({status})")
    _, _, out = http(loc)
    with open(path, "wb") as f:
        f.write(out)
    return len(data), len(out)


def main():
    auth = key()
    progress = load_progress()
    slugs = sorted(build_staging.DONE | build_staging.CUT_QUEUE)
    done = skip = fail = 0
    before_total = after_total = 0
    for slug in slugs:
        path = os.path.join(ROOT, "assets", "items", slug + ".png")
        if not os.path.exists(path):
            print(f"  MISSING {slug}")
            continue
        if progress.get(slug):
            skip += 1
            continue
        try:
            b, a = compress(path, auth)
            progress[slug] = {"before": b, "after": a}
            save_progress(progress)
            before_total += b
            after_total += a
            print(f"  ok {slug}: {b/1e6:.2f}MB -> {a/1e6:.2f}MB")
            done += 1
        except Exception as e:
            print(f"  FAIL {slug}: {type(e).__name__}: {e}")
            fail += 1
    print(f"\nRun: {done} compressed · {skip} skipped · {fail} failed. "
          f"Saved {after_total/1e6:.1f}MB (before {before_total/1e6:.1f}MB).")
    if fail:
        print("Failures:", [s for s in slugs if progress.get(s, {}).get("after") is None and os.path.exists(os.path.join(ROOT, "assets", "items", s + ".png"))][:10])


if __name__ == "__main__":
    main()
