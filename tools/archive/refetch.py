#!/usr/bin/env python3
"""
Dump candidate image URLs for redo products so a better image can be picked.

Usage (from project root):
    python3 tools/refetch.py <slug> [<slug> ...]
    python3 tools/refetch.py --all-redo
"""

import os
import re
import subprocess
import sys
import urllib.parse
from html import unescape

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from new_products import NEW_PRODUCTS  # noqa: E402

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/17.0 Safari/605.1.15"
)

REDO_SLUGS = [
    "rocco-super-smart-fridge",
    "aiaiai-tma-2",
    "wastberg-winkel-base",
    "bellroy-key-cover",
    "orbitkey-airtag-case",
    "northface-thermoball-traction",
    "crustmill",
]

BY_SLUG = {slug: (brand, name, cat, size, url) for slug, brand, name, cat, size, url in NEW_PRODUCTS}


def curl(url, timeout=30):
    r = subprocess.run([
        "curl", "-sL", "--max-time", str(timeout), "-A", UA,
        "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "-H", "Accept-Language: en-US,en;q=0.9",
        "-H", "Referer: https://www.google.com/",
        url,
    ], capture_output=True)
    return r.stdout


def meta(html, prop):
    pat1 = r'<meta[^>]+(?:property|name)=["\']' + re.escape(prop) + r'["\'][^>]*content=["\']([^"\']+)["\']'
    pat2 = r'<meta[^>]+content=["\']([^"\']+)["\'][^>]*(?:property|name)=["\']' + re.escape(prop) + r'["\']'
    m = re.search(pat1, html, re.I) or re.search(pat2, html, re.I)
    return unescape(m.group(1)) if m else None


def absolutize(img, base):
    if not img:
        return None
    img = img.strip()
    if img.startswith("//"):
        return "https:" + img
    if img.startswith("/"):
        p = urllib.parse.urlparse(base)
        return f"{p.scheme}://{p.netloc}{img}"
    return img


def collect(html, base):
    cands = []
    for m in re.finditer(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, re.S | re.I):
        for img in re.findall(r'"image"\s*:\s*("?)([^",}\]]+)', m.group(1)):
            cands.append(img[1])
    for m in re.finditer(r'<img[^>]+src=["\']([^"\']*cdn\.shopify\.com[^"\']*)["\']', html, re.I):
        cands.append(m.group(1))
    cands.append(meta(html, "og:image:secure_url"))
    cands.append(meta(html, "og:image"))
    cands.append(meta(html, "twitter:image"))
    seen, out = set(), []
    for c in cands:
        a = absolutize(c, base)
        if a and a not in seen:
            seen.add(a)
            out.append(a)
    return out


def main():
    slugs = sys.argv[1:]
    if "--all-redo" in slugs:
        slugs = REDO_SLUGS
    for slug in slugs:
        info = BY_SLUG.get(slug)
        if not info:
            print(f"?? {slug} not in manifest")
            continue
        _brand, _name, _cat, _size, url = info
        print(f"\n=== {slug}  ({url}) ===")
        try:
            html = curl(url).decode("utf-8", "replace")
        except Exception as e:
            print("  page fetch failed:", e)
            continue
        for i, c in enumerate(collect(html, url)):
            print(f"  [{i}] {c}")


if __name__ == "__main__":
    main()
