#!/usr/bin/env python3
"""
Drive the real Photoroom web tool (photoroom.com/tools/background-remover)
via the local OpenTabs browser MCP: inject each image into the hidden file
input, invoke the React onChange handler, wait for AI processing, capture the
full-res result blob in-page (chunked, so no save dialogs), and save the
framed PNG + WebP variants into assets/items/.

Usage:
    python3 tools/pr_web_batch.py <id> [<id> ...]
    python3 tools/pr_web_batch.py --all

State (which items succeeded) persists in tools/.pr-web-state.json.
"""

import base64
import io
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import opentabs

from PIL import Image
from process_images import crop_and_square
from optimize_images import emit_variant

TAB = int(os.environ.get("PR_TAB", "1256104729"))
STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".pr-web-state.json")
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DEST = os.path.join(ROOT, "assets", "items")

REMAINING = [
    "veark-sk15-santoku", "serax-bottle-opener", "ugmonk-analog-weekly-kit",
    "ugmonk-bolt-action-pen-onyx", "ugmonk-craft-pen", "ugmonk-multi-pen-tray",
    "hightide-penco-tape-dispenser", "kokuyo-hakoake-scissors",
    "kismas-doric-lamp-01", "hem-udon-chair", "dhs-sand-teapot",
    "eva-solo-nordic-teapot", "standard-equipment-shelving",
    "wastberg-winkel-base", "coteetciel-avon-backpack", "bellroy-key-cover",
    "orbitkey-airtag-case", "northface-thermoball-traction", "crustmill",
    "kal-wall",
]


def exec_js(code, retries=2):
    for _ in range(retries):
        try:
            res = opentabs.rpc("tools/call", {
                "name": "browser_execute_script",
                "arguments": {"tabId": TAB, "code": code},
            })
            raw = res["content"][0]["text"]
            outer = json.loads(raw)
            inner = outer["value"]
            if isinstance(inner, dict) and "value" in inner:
                inner = inner["value"]
            return inner
        except Exception as e:
            time.sleep(2)
    raise RuntimeError("exec_js failed")


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def save_state(st):
    with open(STATE_FILE, "w") as f:
        json.dump(st, f, indent=1)


def prepare_b64(item_id):
    im = Image.open(os.path.join(DEST, item_id + ".png")).convert("RGBA")
    im.thumbnail((1600, 1600), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return base64.b64encode(buf.getvalue()).decode()


def inject_and_process(item_id, b64):
    code = f"""
(() => {{
  window.__auto = {{ done: false, err: null, b64: null, len: 0 }};
  const input = document.querySelector('input[type=file]');
  if (!input) return 'no input';
  const bin = atob("{b64}");
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  const file = new File([bytes], 'img.png', {{ type: 'image/png' }});
  const dt = new DataTransfer();
  dt.items.add(file);
  Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'files').set.call(input, dt.files);
  const k = Object.keys(input).find(k => k.startsWith('__reactProps'));
  if (!k) return 'no react props';
  const h = input[k].onChange;
  h({{ target: input, currentTarget: input, type: 'change', bubbles: true,
       preventDefault(){{}}, stopPropagation(){{}} }});
  return 'injected';
}})()
"""
    r = exec_js(code)
    if r != "injected":
        raise RuntimeError(f"inject failed: {r}")

    # wait for AI processing: the Download button becomes enabled
    deadline = time.time() + 75
    clicked = False
    while time.time() < deadline:
        state = exec_js(
            "(() => { const b=[...document.querySelectorAll('button')]"
            ".find(x=>(x.textContent||'').trim()==='Download');"
            "return b ? (b.disabled ? 'busy' : 'ready') : 'gone'; })()"
        )
        if state == "ready":
            # click Download; the anchor-click patch captures the blob w/o dialog
            exec_js(
                "(() => { const b=[...document.querySelectorAll('button')]"
                ".find(x=>(x.textContent||'').trim()==='Download');"
                "if(b){b.click();return 'clicked';}return 'none'; })()"
            )
            clicked = True
            break
        if state == "gone":
            time.sleep(3)
            continue
        time.sleep(3)
    if not clicked:
        raise RuntimeError("timed out waiting for result")

    deadline = time.time() + 40
    while time.time() < deadline:
        has = exec_js("!!(window.__auto && window.__auto.b64)")
        if has:
            return exec_js("window.__auto.len")
        time.sleep(2)
    raise RuntimeError("timed out waiting for blob capture")


def pull_b64():
    n = exec_js(
        "(() => { const s = window.__auto.b64 || ''; const parts = [];"
        "for (let i = 0; i < s.length; i += 120000) parts.push(s.slice(i, i + 120000));"
        "window.__dlParts = parts; return parts.length; })()"
    )
    parts = []
    for i in range(n):
        parts.append(exec_js(f"window.__dlParts[{i}]"))
    return "".join(parts)


def save_cutout(item_id, b64):
    data = base64.b64decode(b64)
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise RuntimeError("result is not a PNG")
    im = Image.open(io.BytesIO(data)).convert("RGBA")
    w, h = im.size
    corners = [im.getpixel((1, 1))[3], im.getpixel((w - 2, 1))[3],
               im.getpixel((1, h - 2))[3], im.getpixel((w - 2, h - 2))[3]]
    if any(a > 5 for a in corners):
        raise RuntimeError(f"cutout not transparent: corners {corners}")
    framed = crop_and_square(im)
    framed.save(os.path.join(DEST, item_id + ".png"), "PNG", optimize=True)
    emit_variant(framed, os.path.join(DEST, f"{item_id}-800.webp"), 800)
    emit_variant(framed, os.path.join(DEST, f"{item_id}-1600.webp"), 1600)
    return framed.size


def main():
    args = sys.argv[1:]
    ids = REMAINING if (args and args[0] == "--all") else args
    state = load_state()
    ok = fail = 0
    for item in ids:
        if state.get(item):
            print(f"  skip {item} (already done)")
            ok += 1
            continue
        try:
            b64 = prepare_b64(item)
            n = inject_and_process(item, b64)
            full = pull_b64()
            size = save_cutout(item, full)
            state[item] = True
            save_state(state)
            print(f"  ok    {item}  ({n} bytes -> {size})")
            ok += 1
        except Exception as e:
            print(f"  FAIL  {item}: {e}")
            fail += 1
    print(f"\nDone. {ok} ok · {fail} failed.")


if __name__ == "__main__":
    main()
