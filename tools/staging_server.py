#!/usr/bin/env python3
"""Local API for the staging review page.

The staging page's 🖼 button ("remove background") POSTs the product slug
here; this server drives the REAL Photoroom web tool (open in the user's
browser via OpenTabs MCP), saves the cutout + WebP variants into
assets/items/, rebuilds staging.html, and returns the new thumb/full data
URIs so the card updates live.

Endpoints:
    GET  /                      -> staging.html
    GET  /api/status            -> {"ok": true}
    POST /api/remove-bg         -> {"slug": "..."} -> {"ok": true, thumb, full, size}
                                   or {"ok": false, error}
"""

import base64
import io
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)

import opentabs
import photoroom_cut
import build_staging

from PIL import Image

PHOTOROOM_URL = "https://www.photoroom.com/tools/background-remover"
PORT = int(os.environ.get("STAGING_API_PORT", "8125"))
STAGING_DIR = os.path.join(TOOLS, "staging")
DEST = os.path.join(ROOT, "assets", "items")
CUT_LOCK = threading.Lock()


def _rpc_tabs():
    res = opentabs.rpc("tools/call", {"name": "browser_list_tabs", "arguments": {}})
    text = res["content"][0]["text"]
    return json.loads(text) if isinstance(text, str) else text


def find_photoroom_tab():
    """Return the id of an open Photoroom background-remover tab, else open one."""
    for t in _rpc_tabs():
        if "photoroom" in (t.get("url") or "").lower():
            return t["id"]
    opentabs.rpc("tools/call", {
        "name": "browser_open_tab",
        "arguments": {"url": PHOTOROOM_URL},
    })
    for _ in range(20):
        time.sleep(1.5)
        for t in _rpc_tabs():
            if "photoroom" in (t.get("url") or "").lower():
                return t["id"]
    raise RuntimeError("could not open a Photoroom tab")


def cut_source(slug):
    """Prefer the ORIGINAL image (with background) from tools/staging/ so the
    cut is meaningful; fall back to the current master PNG."""
    if os.path.isdir(STAGING_DIR):
        for f in sorted(os.listdir(STAGING_DIR)):
            base, ext = os.path.splitext(f)
            if base == slug and ext.lower() in (".jpg", ".jpeg", ".png", ".webp", ".avif"):
                return os.path.join(STAGING_DIR, f)
    final = os.path.join(DEST, slug + ".png")
    if os.path.exists(final):
        return final
    raise FileNotFoundError(f"no source image for {slug}")


def prepare_b64(path):
    im = Image.open(path).convert("RGBA")
    im.thumbnail((1600, 1600), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return base64.b64encode(buf.getvalue()).decode()


def cut_slug(slug):
    """Run the real Photoroom cut for one slug. Returns the framed size."""
    with CUT_LOCK:
        photoroom_cut.TAB = find_photoroom_tab()
        b64 = prepare_b64(cut_source(slug))
        photoroom_cut.install_patches()
        photoroom_cut.inject_and_process(slug, b64)
        full = photoroom_cut.pull_b64()
        return photoroom_cut.save_cutout(slug, full)


def rebuild_staging():
    build_staging.main()


def thumb_full_uris(slug):
    img = Image.open(os.path.join(DEST, slug + ".png"))
    thumb = build_staging.to_data_uri(img, build_staging.THUMB_LONG)
    full = build_staging.to_full_jpeg_uri(img, build_staging.FULL_LONG)
    return thumb, full


class Handler(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-store")

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self.path == "/api/status":
            self._json({"ok": True, "port": PORT})
            return
        if self.path in ("/", "/staging.html"):
            path = os.path.join(ROOT, "staging.html")
            if not os.path.exists(path):
                rebuild_staging()
            with open(path, "rb") as f:
                body = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self._cors()
            self.end_headers()
            self.wfile.write(body)
            return
        self._json({"ok": False, "error": "not found"}, 404)

    def do_POST(self):
        if self.path != "/api/remove-bg":
            self._json({"ok": False, "error": "not found"}, 404)
            return
        try:
            n = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(n) or b"{}")
            slug = str(data.get("slug", "")).strip()
            if not slug:
                self._json({"ok": False, "error": "missing slug"}, 400)
                return
            size = cut_slug(slug)
            rebuild_staging()
            thumb, full = thumb_full_uris(slug)
            self._json({"ok": True, "slug": slug, "size": list(size), "thumb": thumb, "full": full})
        except FileNotFoundError as e:
            self._json({"ok": False, "error": str(e)}, 404)
        except Exception as e:
            self._json({"ok": False, "error": f"{type(e).__name__}: {e}"}, 500)

    def log_message(self, fmt, *args):
        sys.stderr.write("[staging-api] %s\n" % (fmt % args))


if __name__ == "__main__":
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"staging API on http://127.0.0.1:{PORT}", flush=True)
    srv.serve_forever()
