#!/usr/bin/env python3
"""Cut every slug in build_staging.CUT_QUEUE through the REAL Photoroom web
tool (via OpenTabs) — one at a time, resumably. Skips slugs already done
(tools/.cut-progress.json). Prints a line per slug.

Usage:
    python3 tools/cut_queue.py
"""

import json
import os
import sys
import time

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)

import build_staging  # noqa: E402
import staging_server  # noqa: E402

PROGRESS = os.path.join(TOOLS, ".cut-progress.json")


def load_progress():
    if os.path.exists(PROGRESS):
        with open(PROGRESS) as f:
            return json.load(f)
    return {}


def save_progress(p):
    with open(PROGRESS, "w") as f:
        json.dump(p, f, indent=1)


def main():
    progress = load_progress()
    queue = sorted(build_staging.CUT_QUEUE)
    ok = fail = skip = 0
    for slug in queue:
        if progress.get(slug):
            print(f"  skip {slug} (already cut)")
            skip += 1
            continue
        t0 = time.time()
        try:
            size = staging_server.cut_slug(slug)
            progress[slug] = {"ok": True, "size": list(size), "secs": round(time.time() - t0, 1)}
            save_progress(progress)
            print(f"  OK   {slug}  {list(size)}  ({time.time()-t0:.0f}s)")
            ok += 1
        except Exception as e:
            progress[slug] = {"ok": False, "error": f"{type(e).__name__}: {e}"}
            save_progress(progress)
            print(f"  FAIL {slug}: {e}")
            fail += 1
    print(f"\nDone this run: {ok} ok · {fail} failed · {skip} skipped (of {len(queue)}).")
    if fail:
        print("Failures:", [s for s in queue if progress.get(s, {}).get("ok") is False])


if __name__ == "__main__":
    main()
