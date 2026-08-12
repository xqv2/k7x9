#!/usr/bin/env python3
"""Probe candidate canonical (brand-site) URLs for the batch-3 products.
For each (slug, token, [candidates]) prints which candidate resolves and
whose og:title contains the token."""

import re
import subprocess
import sys

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15")

CANDIDATES = [
    # (slug, og:title token, [urls])
    ("temple-flashlight",  "temple",  ["https://craighill.com/products/temple-flashlight"]),
    ("desk-knife",         "desk",    ["https://craighill.com/products/desk-knife"]),
    ("eyewear-stand",      "eyewear", ["https://craighill.com/products/eyewear-stand"]),
    ("perch-bookmark",     "perch",   ["https://craighill.com/products/perch-bookmark"]),
    ("kepler-pen",         "kepler",  ["https://craighill.com/products/kepler-pen"]),
    ("the-palmer",         "palmer",  ["https://thejamesbrand.com/products/the-palmer"]),
    ("aiden-coffee",       "aiden",   ["https://fellowproducts.com/products/aiden-precision-coffee-maker"]),
    ("ooni-karu-12",       "karu",    ["https://ooni.com/products/ooni-karu-12"]),
    ("ratio-six",          "six",     ["https://ratio.co/products/ratio-six"]),
    ("finex-skillet",      "finex",   ["https://finexusa.com/products/finex-12-skillet", "https://finexusa.com/collections/skillets"]),
    ("keysmart-rugged",    "rugged",  ["https://www.getkeysmart.com/products/keysmart-rugged"]),
    ("oru-bay",            "bay",     ["https://www.orukayak.com/products/oru-bay"]),
    ("pinned-soundstick",  "sound",   ["https://pinnedgolf.com/products/sound-stick-pro"]),
    ("weber-eg1",          "eg-1",    ["https://weberworkshops.com/products/eg-1"]),
    ("weber-key",          "key",     ["https://weberworkshops.com/products/key"]),
    ("weber-hg2",          "hg-2",    ["https://weberworkshops.com/products/hg-2"]),
    ("cwandt-pen-type-a",  "type-a",  ["https://cwandt.com/products/pen-type-a"]),
    ("moonbikes",          "moonbike",["https://moonbikes.com/"]),
    ("barebones-flatware", "flatware",["https://barebonesliving.com/products/flatware-set"]),
    ("balmuda-toaster",    "toaster", ["https://www.balmuda.com/pages/balmuda-the-toaster", "https://www.balmuda.com/products/balmuda-the-toaster"]),
    ("balmuda-teppanyaki", "teppanyaki", ["https://www.balmuda.com/pages/balmuda-the-teppanyaki"]),
    ("balmuda-speaker",    "speaker", ["https://www.balmuda.com/pages/balmuda-the-speaker"]),
    ("balmuda-moonkettle", "moonkettle", ["https://www.balmuda.com/pages/balmuda-moonkettle"]),
    ("balmuda-clock",      "clock",   ["https://www.balmuda.com/pages/balmuda-the-clock"]),
    ("balmuda-naturewind", "naturewind", ["https://www.balmuda.com/pages/balmuda-naturewind"]),
    ("project-acdc",       "ac/dc",   ["https://www.project-audio.com/en/product/ac-dc-limited-edition-turntable"]),
]


def curl(url):
    return subprocess.run(["curl", "-sL", "--max-time", "20", "-A", UA, url],
                          capture_output=True).stdout


def og_title(html):
    m = re.search(r'<meta[^>]+(?:property|name)=["\']og:title["\'][^>]*content=["\']([^"\']+)', html)
    if not m:
        m = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]*(?:property|name)=["\']og:title["\']', html)
    return m.group(1)[:90] if m else None


def main():
    only = sys.argv[1:] if len(sys.argv) > 1 else None
    for slug, token, urls in CANDIDATES:
        if only and slug not in only:
            continue
        print(f"\n== {slug}  (want: {token})")
        for u in urls:
            try:
                h = curl(u)
            except Exception as e:
                print(f"   {u}  ERR {e}")
                continue
            t = og_title(h.decode("utf-8", "replace"))
            ok = "OK " if (t and token.lower() in t.lower()) else "?? "
            print(f"   {ok}{u}")
            if t:
                print(f"        -> {t}")


if __name__ == "__main__":
    main()
