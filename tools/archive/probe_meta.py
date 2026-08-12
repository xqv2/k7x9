#!/usr/bin/env python3
"""Fetch a list of URLs and print title / og:title / og:description to help
identify what each link is (used when building the new-products manifest)."""

import re
import subprocess
import sys

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15")


def curl(url):
    r = subprocess.run([
        "curl", "-sL", "--max-time", "25", "-A", UA, url,
    ], capture_output=True)
    return r.stdout.decode("utf-8", "replace")


def meta(html, prop):
    pats = [
        r'<meta[^>]+property=["\']' + re.escape(prop) + r'["\'][^>]*content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]*property=["\']' + re.escape(prop) + r'["\']',
    ]
    for p in pats:
        m = re.search(p, html, re.I)
        if m:
            return m.group(1)[:130]
    return None


def main():
    for url in sys.argv[1:]:
        print(f"\n=== {url}")
        html = curl(url)
        t = re.search(r"<title>([^<]{0,130})", html, re.I)
        print("title:   ", t.group(1).strip() if t else "?")
        print("og:title:", meta(html, "og:title") or "?")
        print("og:desc: ", meta(html, "og:description") or "?")


if __name__ == "__main__":
    main()
