#!/usr/bin/env python3
"""
Compress all product master PNGs in assets/items/ before the bulk GitHub upload.

Why: the site only ever renders the -800/-1600.webp variants via <picture>.
The .png master is used solely as the <img> fallback and as the source for
regenerating WebPs (admin panel). Nothing in the pipeline needs a master
larger than 1600px, yet many are 2000-5000px.

Strategy (lossless-to-display, per file):
  1. Downscale to 1600px long edge (LANCZOS), keep alpha.
  2. Encode two candidates:
       a. optimized RGB/RGBA PNG (lossless)
       b. 256-color palette PNG (FASTOCTREE + Floyd-Steinberg) — PIL preserves
          mid-range alpha here, so cutout edges stay anti-aliased
  3. Keep whichever is smaller; rewrite in place only if it saves >= 10%.

Safety:
  - Untracked masters (no git history copy) are backed up at full resolution
    to tools/backup-fullres/ before compression (gitignored).
  - Re-running is safe: already-compressed files fail the >=10% rule and are
    left alone.
"""
import io
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ITEMS = os.path.join(ROOT, "assets", "items")
BACKUP = os.path.join(ROOT, "tools", "backup-fullres")
MAX_EDGE = 1600
MIN_SAVING = 0.10  # rewrite only if new size < 90% of old
SKIP_BELOW = 200 * 1024  # never bother files already this small

from PIL import Image


def is_untracked(path):
    rel = os.path.relpath(path, ROOT)
    out = subprocess.run(
        ["git", "status", "--short", "--", rel],
        capture_output=True, text=True, cwd=ROOT,
    ).stdout.strip()
    return out.startswith("??")


def encode_candidates(img):
    buf_rgb = io.BytesIO()
    img.save(buf_rgb, "PNG", optimize=True)
    q = img.quantize(colors=256, method=Image.FASTOCTREE,
                     dither=Image.FLOYDSTEINBERG)
    buf_8 = io.BytesIO()
    q.save(buf_8, "PNG", optimize=True)
    return buf_rgb.getvalue(), buf_8.getvalue()


def main():
    files = sorted(f for f in os.listdir(ITEMS) if f.endswith(".png"))
    if not files:
        print("no masters found"); return

    os.makedirs(BACKUP, exist_ok=True)
    total_before = total_after = 0
    changed = skipped = backed_up = 0

    for f in files:
        path = os.path.join(ITEMS, f)
        orig_size = os.path.getsize(path)
        total_before += orig_size

        if orig_size < SKIP_BELOW:
            total_after += orig_size
            skipped += 1
            continue

        img = Image.open(path)
        w, h = img.size
        if max(w, h) > MAX_EDGE:
            r = MAX_EDGE / max(w, h)
            img = img.resize((max(1, round(w * r)), max(1, round(h * r))),
                             Image.LANCZOS)

        # Backup untracked full-res masters (tracked ones live in git history)
        if not is_untracked(path):
            pass
        elif not os.path.exists(os.path.join(BACKUP, f)):
            shutil.copy2(path, os.path.join(BACKUP, f))
            backed_up += 1

        try:
            rgb_data, png8_data = encode_candidates(img)
        except Exception as exc:
            print(f"  SKIP  {f}: {exc}")
            total_after += orig_size
            continue

        new_data = min((rgb_data, png8_data), key=len)
        if len(new_data) < orig_size * (1 - MIN_SAVING):
            with open(path, "wb") as fh:
                fh.write(new_data)
            total_after += len(new_data)
            changed += 1
            kind = "png8" if new_data is png8_data else "rgb"
            print(f"  ok    {f}: {orig_size//1024}KB -> {len(new_data)//1024}KB ({kind})")
        else:
            total_after += orig_size
            skipped += 1

    print(f"\n{len(files)} masters: {total_before/1e6:.1f}MB -> {total_after/1e6:.1f}MB "
          f"({(total_before-total_after)/1e6:.1f}MB saved)")
    print(f"{changed} rewritten, {skipped} left as-is, {backed_up} full-res backups "
          f"in tools/backup-fullres/")


if __name__ == "__main__":
    sys.exit(main())
