#!/usr/bin/env python3
"""
Fetch hero images for the new-product batch (tools/new_products.py).

Downloads the product page, extracts the best hero image (og:image with
JSON-LD / Shopify-CDN / first-product-img fallbacks), and saves it to
tools/staging/<slug>.<ext> for the background-removal step.

Usage (from project root):
    python3 tools/fetch_new.py
"""

import os
import re
import subprocess
import sys
import urllib.parse
from html import unescape

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from new_products import NEW_PRODUCTS  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
STAGING = os.path.normpath(os.path.join(HERE, "staging"))
os.makedirs(STAGING, exist_ok=True)

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/17.0 Safari/605.1.15"
)


def curl(url, timeout=30, binary=False):
    """Fetch with curl: follows redirects, tolerant TLS, browser-ish headers."""
    args = [
        "curl", "-sL", "--max-time", str(timeout),
        "-A", UA,
        "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "-H", "Accept-Language: en-US,en;q=0.9",
        "-H", "Referer: https://www.google.com/",
        url,
    ]
    r = subprocess.run(args, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"curl failed ({r.returncode}): {r.stderr.decode('utf-8', 'replace')[:200]}")
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


def jsonld_images(html):
    """Pull image URLs out of <script type="application/ld+json"> blocks."""
    found = []
    for m in re.finditer(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, re.S | re.I):
        text = m.group(1)
        for img in re.findall(r'"image"\s*:\s*"([^"]+)"', text):
            found.append(img)
        for img in re.findall(r'"image"\s*:\s*\[\s*"([^"]+)"', text):
            found.append(img)
    return found


def shopify_images(html):
    """First few cdn.shopify.com URLs in <img> tags (Shopify stores)."""
    found = []
    for m in re.finditer(r'<img[^>]+src=["\']([^"\']*cdn\.shopify\.com[^"\']*)["\']', html, re.I):
        found.append(m.group(1))
    return found


def first_product_img(html):
    """First <img> whose src/srcdir looks like a big product shot."""
    for m in re.finditer(r'<img[^>]+(?:src|data-src)=["\']([^"\']+)["\'][^>]*>', html, re.I):
        src = unescape(m.group(1))
        low = src.lower()
        if any(k in low for k in ("logo", "icon", "favicon", "pixel", "badge", "sprite")):
            continue
        if src.startswith("data:"):
            continue
        return src
    return None


def pick_image(html, url):
    cands = []
    cands.append(meta(html, "og:image:secure_url"))
    cands.append(meta(html, "og:image"))
    cands.append(meta(html, "twitter:image"))
    cands += jsonld_images(html)
    cands += shopify_images(html)
    cands.append(first_product_img(html))
    seen = set()
    out = []
    for c in cands:
        a = absolutize(c, url)
        if a and a not in seen:
            seen.add(a)
            out.append(a)
    return out


def guess_ext(img_url, content_type):
    ct = (content_type or "").lower()
    if "jpeg" in ct or "jpg" in ct: return "jpg"
    if "png" in ct: return "png"
    if "webp" in ct: return "webp"
    if "avif" in ct: return "avif"
    path = urllib.parse.urlparse(img_url).path.lower()
    for ext in ("jpg", "jpeg", "png", "webp", "avif"):
        if path.endswith("." + ext):
            return ext
    return "jpg"


def download(img_url, dest_no_ext):
    data = curl(img_url)
    # curl -sL discards headers; re-run with -D - to sniff content type.
    probe = subprocess.run([
        "curl", "-sIL", "--max-time", "30",
        "-A", UA,
        "-H", "Referer: https://www.google.com/",
        img_url,
    ], capture_output=True)
    head = probe.stdout.decode("utf-8", "replace").lower()
    ct = ""
    m = re.search(r"content-type:\s*([^\r\n]+)", head)
    if m:
        ct = m.group(1).strip()
    ext = guess_ext(img_url, ct)
    path = dest_no_ext + "." + ext
    with open(path, "wb") as f:
        f.write(data)
    return path


def main():
    ok = fail = skip = 0
    for slug, _brand, _name, _cat, _size, url in NEW_PRODUCTS:
        # Skip if any file already exists for this slug.
        existing = [f for f in os.listdir(STAGING) if f.startswith(slug + ".")]
        if existing:
            print(f"  skip   {slug}  ({existing[0]})")
            skip += 1
            continue
        try:
            raw = curl(url)
            html = raw.decode("utf-8", "replace")
        except Exception as e:
            print(f"  FAIL   {slug}  page: {e}")
            fail += 1
            continue
        cands = pick_image(html, url)
        if not cands:
            print(f"  FAIL   {slug}  no hero image found")
            fail += 1
            continue
        got = None
        for img_url in cands:
            try:
                got = download(img_url, os.path.join(STAGING, slug))
                break
            except Exception as e:
                print(f"  -      {slug}  candidate {img_url[:80]} failed: {e}")
        if got:
            print(f"  ok     {slug}  -> {os.path.basename(got)}")
            ok += 1
        else:
            print(f"  FAIL   {slug}  all image candidates failed")
            fail += 1

    print(f"\nDone. {ok} downloaded · {skip} already had · {fail} failed.")
    if fail:
        print("Failed slugs need manual attention — see messages above.")


if __name__ == "__main__":
    main()
