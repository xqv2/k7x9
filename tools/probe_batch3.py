#!/usr/bin/env python3
"""Probe Uncrate product pages: og:title + og:description to identify the
brand/product, so we can find the canonical (brand-site) product URL."""

import re
import subprocess
import sys

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15")

URLS = [
    "https://shop.uncrate.com/products/temple-flashlight",
    "https://shop.uncrate.com/products/pizza-axe",
    "https://shop.uncrate.com/products/astroflex-chelsea-boot",
    "https://shop.uncrate.com/products/the-palmer",
    "https://shop.uncrate.com/products/dotti-super-scrubber-odyssey",
    "https://shop.uncrate.com/products/blacksmith-knife-trio",
    "https://shop.uncrate.com/products/balmuda-the-teppanyaki",
    "https://shop.uncrate.com/products/blacksmith-ulu-knife",
    "https://shop.uncrate.com/products/scoopthat-deluxe",
    "https://shop.uncrate.com/products/aiden-precision-coffee-maker-fellow",
    "https://shop.uncrate.com/products/the-hg-2",
    "https://shop.uncrate.com/products/black-creek-black-rolling-pin",
    "https://shop.uncrate.com/products/clyde-electric-kettle",
    "https://shop.uncrate.com/products/zebra-wood-bbq-6-pc-knife-set",
    "https://shop.uncrate.com/products/tally-pro-precision-scale-studio-edition",
    "https://shop.uncrate.com/products/forged-steel-12-piece-giotto-knife-block-set",
    "https://shop.uncrate.com/products/jet-black-forged-kitchen-shears",
    "https://shop.uncrate.com/products/the-eg-1",
    "https://shop.uncrate.com/products/porsche-design-carving-set",
    "https://shop.uncrate.com/products/ooni-karu-12-portable-pizza-oven",
    "https://shop.uncrate.com/products/the-key",
    "https://shop.uncrate.com/products/alessi-water-kettle",
    "https://shop.uncrate.com/products/porsche-design-universal-kitchen-knife",
    "https://shop.uncrate.com/products/porsche-design-steak-knives",
    "https://shop.uncrate.com/products/ratio-six-coffee-machine",
    "https://shop.uncrate.com/products/finex-cast-iron-skillet",
    "https://shop.uncrate.com/products/moonkettle",
    "https://shop.uncrate.com/products/flatware-set",
    "https://shop.uncrate.com/products/balmuda-the-toaster-pro",
    "https://shop.uncrate.com/products/10-bread-knife",
    "https://shop.uncrate.com/products/cast-iron-grill-press",
    "https://shop.uncrate.com/products/5-9-quart-enameled-cast-iron-dutch-oven",
    "https://shop.uncrate.com/products/casio-moonphase-analog-watch",
    "https://shop.uncrate.com/products/hegid-celeste-steel-watch",
    "https://shop.uncrate.com/products/wayne-enterprises-x-bell-ross-br-03-skeleton-watch",
    "https://shop.uncrate.com/products/the-story-of-porsche-1",
    "https://shop.uncrate.com/products/churchill-wit-and-wisdom-1",
    "https://shop.uncrate.com/products/james-bond-style",
    "https://shop.uncrate.com/products/latelier-du-vin-soft-machine-wine-key",
    "https://shop.uncrate.com/products/luca-humidor-cabinet",
    "https://shop.uncrate.com/products/l-atelier-du-vin-oeno-wine-pull",
    "https://shop.uncrate.com/products/the-clock",
    "https://shop.uncrate.com/products/eyewear-stand",
    "https://shop.uncrate.com/products/pen-type-a",
    "https://shop.uncrate.com/products/perch-bookmark",
    "https://shop.uncrate.com/products/kepler-pen",
    "https://shop.uncrate.com/products/multitool-pen-7-in-1-phone-stand",
    "https://shop.uncrate.com/products/naturewind-studio",
    "https://shop.uncrate.com/products/moonbikes-x-uncrate-electric-snow-mobile",
    "https://shop.uncrate.com/products/keysmart-rugged-extra-durable-key-holder-expandable-to-hold-up-to-14-keys",
    "https://shop.uncrate.com/products/oru-bay-black-edition",
    "https://shop.uncrate.com/products/sound-stick-pro",
    "https://shop.uncrate.com/products/pro-ject-audio-ac-dc-limited-editon-turntable",
    "https://shop.uncrate.com/products/balmuda-the-speaker",
    "https://shop.uncrate.com/products/brionvega-radiofonografo-record-console",
]


def meta(html, prop):
    pat1 = r'<meta[^>]+(?:property|name)=["\']' + re.escape(prop) + r'["\'][^>]*content=["\']([^"\']+)["\']'
    pat2 = r'<meta[^>]+content=["\']([^"\']+)["\'][^>]*(?:property|name)=["\']' + re.escape(prop) + r'["\']'
    m = re.search(pat1, html, re.I) or re.search(pat2, html, re.I)
    return m.group(1)[:150] if m else None


def main():
    for url in URLS:
        slug = url.rstrip("/").split("/")[-1]
        r = subprocess.run(["curl", "-sL", "--max-time", "25", "-A", UA, url],
                           capture_output=True)
        html = r.stdout.decode("utf-8", "replace")
        t = meta(html, "og:title") or meta(html, "twitter:title") or "?"
        d = meta(html, "og:description") or ""
        print(f"{slug}\t{t}\t{d[:160]}")


if __name__ == "__main__":
    main()
