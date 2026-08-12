#!/usr/bin/env python3
"""
Batch background removal via the Photoroom API (sdk.photoroom.com/v1/segment),
then re-frame the cutout and emit WebP variants using the repo's own helpers.

Usage:
    PHOTOROOM_API_KEY=... python3 tools/photoroom_bg.py <id> [<id> ...]
    PHOTOROOM_API_KEY=... python3 tools/photoroom_bg.py --all-keepbg

Originals (png + webp) are copied to tools/.bg-backup/<id>/ before overwriting.
"""

import os
import shutil
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
DEST = os.path.join(ROOT, "assets", "items")
BACKUP = os.path.join(HERE, ".bg-backup")

sys.path.insert(0, HERE)
from process_images import crop_and_square  # noqa: E402
from optimize_images import emit_variant    # noqa: E402

ENDPOINT = "https://sdk.photoroom.com/v1/segment"
API_KEY = os.environ.get("PHOTOROOM_API_KEY")

KEEP_BG = [
    "aulumu-battery-pack",
    "satechi-headphone-stand",
    "rocco-super-smart-fridge",
    "twemco-bq-17",
    "aiaiai-tma-2",
    "transparent-turntable",
    "tid-no-1",
    "veark-sk15-santoku",
    "serax-bottle-opener",
    "ugmonk-analog-weekly-kit",
    "ugmonk-bolt-action-pen-onyx",
    "ugmonk-craft-pen",
    "ugmonk-multi-pen-tray",
    "hightide-penco-tape-dispenser",
    "kokuyo-hakoake-scissors",
    "kismas-doric-lamp-01",
    "hem-udon-chair",
    "dhs-sand-teapot",
    "eva-solo-nordic-teapot",
    "standard-equipment-shelving",
    "wastberg-winkel-base",
    "coteetciel-avon-backpack",
    "bellroy-key-cover",
    "orbitkey-airtag-case",
    "northface-thermoball-traction",
    "crustmill",
    "kal-wall",
]


def backup(item_id):
    bdir = os.path.join(BACKUP, item_id)
    os.makedirs(bdir, exist_ok=True)
    for suffix in (".png", "-800.webp", "-1600.webp"):
        src = os.path.join(DEST, item_id + suffix)
        dst = os.path.join(bdir, item_id + suffix)
        if os.path.exists(src) and not os.path.exists(dst):
            shutil.copy2(src, dst)


def segment_local(src_path):
    """On-device AI background removal via rembg (same class of model)."""
    from rembg import remove, new_session
    import io
    with open(src_path, "rb") as f:
        data = f.read()
    try:
        out = remove(data, session=_local_session())
    except Exception:
        # fall back to a fresh session if the cached one is stale
        _local_session.cache = None
        out = remove(data, session=_local_session())
    return bytes(out)


_local_session_cache = {}


def _local_session():
    if "sess" not in _local_session_cache:
        print("  ... loading local model (first run downloads ~170 MB)")
        from rembg import new_session
        _local_session_cache["sess"] = new_session("u2net")
    return _local_session_cache["sess"]


def segment(src_path):
    """POST an image to Photoroom; returns the cutout PNG bytes."""
    with open(src_path, "rb") as f:
        img = f.read()
    boundary = "----photoroom" + os.urandom(6).hex()

    def field(name, value, filename=None, ctype=None):
        head = f"--{boundary}\r\n".encode()
        if filename:
            head += f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode()
            head += f"Content-Type: {ctype}\r\n".encode()
        else:
            head += f'Content-Disposition: form-data; name="{name}"\r\n'.encode()
        return head + b"\r\n" + value + b"\r\n"

    body = b""
    body += field("image_file", img, filename="image.png", ctype="image/png")
    body += field("format", b"png")
    body += f"--{boundary}--\r\n".encode()

    req = urllib.request.Request(ENDPOINT, data=body, method="POST")
    req.add_header("x-api-key", API_KEY)
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:300]
        raise RuntimeError(f"HTTP {e.code}: {detail}")


def verify_transparent(cutout, item_id):
    """Corners must have alpha 0 for a real cutout."""
    from PIL import Image
    im = Image.open(cutout).convert("RGBA")
    w, h = im.size
    corners = [im.getpixel((1, 1)), im.getpixel((w - 2, 1)),
               im.getpixel((1, h - 2)), im.getpixel((w - 2, h - 2))]
    if any(c[3] > 5 for c in corners):
        return False
    return True


def process(item_id):
    src = os.path.join(DEST, item_id + ".png")
    if not os.path.exists(src):
        print(f"  SKIP  {item_id}: no source png")
        return False
    backup(item_id)
    try:
        data = segment(src)
    except Exception as e:
        print(f"  FAIL  {item_id}: {e}")
        return False
    if not data or data[:8] != b"\x89PNG\r\n\x1a\n":
        print(f"  FAIL  {item_id}: response is not a PNG ({data[:60]!r})")
        return False

    from PIL import Image
    import io
    tmp = os.path.join(BACKUP, item_id + ".cut.png")
    with open(tmp, "wb") as f:
        f.write(data)
    if not verify_transparent(tmp, item_id):
        print(f"  FAIL  {item_id}: cutout has no transparent corners — likely a bad segment")
        os.remove(tmp)
        return False

    framed = crop_and_square(Image.open(tmp))
    framed.save(src, "PNG", optimize=True)
    os.remove(tmp)
    emit_variant(framed, os.path.join(DEST, f"{item_id}-800.webp"), 800)
    emit_variant(framed, os.path.join(DEST, f"{item_id}-1600.webp"), 1600)
    print(f"  ok    {item_id}  (cutout {framed.size[0]}x{framed.size[1]})")
    return True


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    use_local = "--local" in args
    if not use_local and not API_KEY:
        sys.exit("set PHOTOROOM_API_KEY in the environment (or use --local)")
    if args[0] == "--all-keepbg":
        ids = KEEP_BG
    else:
        ids = [a for a in args if not a.startswith("--")]
    if use_local:
        globals()["segment"] = segment_local
    ok = fail = 0
    for i, item_id in enumerate(ids):
        if process(item_id):
            ok += 1
        else:
            fail += 1
        if i < len(ids) - 1 and not use_local:
            time.sleep(0.4)
    print(f"\nDone. {ok} background-removed · {fail} failed.")
    print(f"Originals backed up in {BACKUP}/")


if __name__ == "__main__":
    main()
