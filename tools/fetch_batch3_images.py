#!/usr/bin/env python3
"""
Fetch batch-3 hero images from shop.uncrate.com product pages.

The user's rule: IMAGES come from shop.uncrate.com (easy to extract);
the LINK in the manifest points to the original brand site.

Maps manifest slug -> shop.uncrate.com product slug, grabs og:image.
"""

import re
import subprocess
import urllib.parse

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15")

# manifest slug -> uncrate product slug
UNC = {
    "jamesbrand-the-palmer":        "the-palmer",
    "marcellin-pizza-axe":          "pizza-axe",
    "marcellin-knife-trio":         "blacksmith-knife-trio",
    "marcellin-ulu-knife":          "blacksmith-ulu-knife",
    "marcellin-grill-press":        "cast-iron-grill-press",
    "marcellin-dutch-oven":         "5-9-quart-enameled-cast-iron-dutch-oven",
    "thatinventions-scoopthat":     "scoopthat-deluxe",
    "dotti-super-scrubber":         "dotti-super-scrubber-odyssey",
    "blackcreek-rolling-pin":       "black-creek-black-rolling-pin",
    "schmidt-zebra-wood-set":       "zebra-wood-bbq-6-pc-knife-set",
    "schmidt-giotto-set":           "forged-steel-12-piece-giotto-knife-block-set",
    "schmidt-shears":               "jet-black-forged-kitchen-shears",
    "steelport-bread-knife":        "10-bread-knife",
    "atech-multitool-pen":          "multitool-pen-7-in-1-phone-stand",
    "cwandt-pen-type-a":            "pen-type-a",
    "craighill-eyewear-stand":      "eyewear-stand",
    "craighill-perch-bookmark":     "perch-bookmark",
    "craighill-kepler-pen":         "kepler-pen",
    "fellow-aiden":                 "aiden-precision-coffee-maker-fellow",
    "fellow-clyde-kettle":          "clyde-electric-kettle",
    "fellow-tally-pro":             "tally-pro-precision-scale-studio-edition",
    "weber-eg-1":                   "the-eg-1",
    "weber-hg-2":                   "the-hg-2",
    "weber-the-key":                "the-key",
    "ratio-six":                    "ratio-six-coffee-machine",
    "ooni-karu-12":                 "ooni-karu-12-portable-pizza-oven",
    "finex-skillet":                "finex-cast-iron-skillet",
    "alessi-9091-kettle":           "alessi-water-kettle",
    "barebones-flatware":           "flatware-set",
    "balmuda-toaster-pro":          "balmuda-the-toaster-pro",
    "balmuda-teppanyaki":           "balmuda-the-teppanyaki",
    "balmuda-moonkettle":           "moonkettle",
    "balmuda-the-clock":            "the-clock",
    "balmuda-naturewind":           "naturewind-studio",
    "balmuda-the-speaker":          "balmuda-the-speaker",
    "porsche-design-carving-set":   "porsche-design-carving-set",
    "porsche-design-universal-knife": "porsche-design-universal-kitchen-knife",
    "porsche-design-steak-knives":  "porsche-design-steak-knives",
    "casio-moonphase":              "casio-moonphase-analog-watch",
    "hegid-celeste":                "hegid-celeste-steel-watch",
    "bell-ross-wayne":              "wayne-enterprises-x-bell-ross-br-03-skeleton-watch",
    "story-of-porsche-book":        "the-story-of-porsche-1",
    "churchill-wit-wisdom":         "churchill-wit-and-wisdom-1",
    "james-bond-style-book":        "james-bond-style",
    "latelierduvin-soft-machine":   "latelier-du-vin-soft-machine-wine-key",
    "latelierduvin-oeno":           "l-atelier-du-vin-oeno-wine-pull",
    "moonbikes-x-uncrate":          "moonbikes-x-uncrate-electric-snow-mobile",
    "oru-bay":                      "oru-bay-black-edition",
    "keysmart-rugged":              "keysmart-rugged-extra-durable-key-holder-expandable-to-hold-up-to-14-keys",
    "astroflex-chelsea-boot":       "astroflex-chelsea-boot",
    "pinned-sound-stick":           "sound-stick-pro",
    "project-acdc-turntable":       "pro-ject-audio-ac-dc-limited-editon-turntable",
    "brionvega-radiofonografo":     "brionvega-radiofonografo-record-console",
}


def curl(url):
    return subprocess.run(["curl", "-sL", "--max-time", "25", "-A", UA,
                           "-H", "Referer: https://www.google.com/", url],
                          capture_output=True).stdout


def ogimg(html):
    m = re.search(r'<meta[^>]+(?:property|name)=["\']og:image["\'][^>]*content=["\']([^"\']+)', html)
    if not m:
        m = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]*(?:property|name)=["\']og:image["\']', html)
    return m.group(1) if m else None


def main():
    ok = fail = 0
    for slug, unc_slug in UNC.items():
        page = f"https://shop.uncrate.com/products/{unc_slug}"
        try:
            h = curl(page).decode("utf-8", "replace")
            img = ogimg(h)
            if not img:
                print(f"  FAIL {slug}  no og:image")
                fail += 1
                continue
            if img.startswith("//"):
                img = "https:" + img
            d = curl(img)
            if len(d) < 5000:
                print(f"  FAIL {slug}  tiny image ({len(d)}B)")
                fail += 1
                continue
            path = urllib.parse.urlparse(img).path.lower()
            ext = "jpg"
            for e in ("png", "webp", "avif", "jpeg"):
                if path.endswith("." + e):
                    ext = "png" if e == "png" else ("webp" if e == "webp" else ("avif" if e == "avif" else "jpg"))
                    break
            open(f"tools/staging/{slug}.{ext}", "wb").write(d)
            print(f"  ok   {slug}.{ext} ({len(d)//1024}KB)")
            ok += 1
        except Exception as e:
            print(f"  FAIL {slug}  {e}")
            fail += 1
    print(f"\nDone. {ok} ok · {fail} failed.")


if __name__ == "__main__":
    main()
