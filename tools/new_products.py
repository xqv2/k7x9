"""
Product manifest for the new batch (August 2026).

Each entry: slug (used for the image filename + items.js id), brand, name,
category, size, and the product URL *cleaned* of tracking params
(?ref=goods, ?variant=…, ?country=…, fragments, etc.).

Run tools/fetch_new.py to download hero images for these.
"""

# (slug, brand, name, category, size, url)
NEW_PRODUCTS = [
    # ---- tech ----
    ("aulumu-battery-pack",          "Aulumu",           "Battery Pack",                     "tech",       "small", "https://aulumu.com/products/battery-pack"),
    ("xbloom-original",              "xBloom",           "Original",                         "tech",       "small", "https://xbloom.com/products/xbloom-original"),
    ("satechi-headphone-stand",      "Satechi",          "2-in-1 Headphone Stand",           "tech",       "small", "https://satechi.com/products/2-in-1-headphone-stand-with-wireless-charger"),
    ("aarke-carbonator-3",           "Aarke",            "Carbonator 3",                     "tech",       "small", "https://aarke.us/products/carbonator-3-kit-matte-black"),
    ("rocco-super-smart-fridge",     "Rocco",            "The Super Smart Fridge",           "tech",       "large", "https://roccofridge.com/products/the-super-smart-fridge"),
    ("twemco-bq-17",                 "Twemco",           "BQ-17 Flip Clock",                 "furniture",  "small", "https://madethisera.com/products/twemco-bq-17-digital-perpetual-calendar-flip-clock-%E6%95%B8%E4%BD%8D%E8%90%AC%E5%B9%B4%E6%9B%86%E7%BF%BB%E9%A0%81%E9%90%98-en-cn-version-%E4%B8%AD%E8%8B%B1%E6%96%87%E7%89%88-black-%E9%BB%91%E8%89%B2-wall-clock-%E6%8E%9B%E7%89%86%E9%90%98"),

    # ---- audio ----
    ("aiaiai-tma-2",                 "AiAiAi",           "TMA-2 Modular Headphones",         "audio",      "small", "https://aiaiai.audio/headphones/tma-2-build-your-own/s02h02e02c02"),
    ("transparent-turntable",        "Transparent",      "Turntable",                        "audio",      "large", "https://transpa.rent/us/turntable-black"),

    # ---- watches ----
    ("breitling-chronomat-b01-42",   "Breitling",        "Chronomat B01 42",                 "watches",    "small", "https://www.breitling.com/us-en/watches/chronomat/chronomat-b01-42-my26/RB0158101Q1R1/"),
    ("tid-no-1",                     "TID",              "No. 1",                            "watches",    "small", "https://tidwatches.com/products/tid-no-1-black-dial-black-leather-strap-black-buckle"),

    # ---- tools ----
    ("veark-sk15-santoku",           "Veark",            "SK15 Santoku Knife",               "tools",      "small", "https://veark.com/collections/all-products/products/sk15-single-piece-stainless-steel-santoku-knife-1"),
    ("serax-bottle-opener",          "Serax",            "Bottle Opener",                    "tools",      "small", "https://serax.com/products/bottle-opener-steel-grey-marcel-les-objets-mouleversants"),
    ("steamerystockholm-lint-brush", "Steamery",         "Lint Brush Sand",                  "tools",      "small", "https://steamerystockholm.com/en-ae/products/lint-brush-sand"),

    # ---- stationery ----
    ("ugmonk-analog-weekly-kit",     "Ugmonk",           "Analog Weekly Kit",                "stationery", "small", "https://ugmonk.com/products/analog-weekly-kit"),
    ("ugmonk-bolt-action-pen-onyx",  "Ugmonk",           "Bolt Action Pen Onyx",             "stationery", "small", "https://ugmonk.com/collections/pens/products/bolt-action-pen-onyx"),
    ("ugmonk-craft-pen",             "Ugmonk",           "Craft Multifunctional Pen",        "stationery", "small", "https://ugmonk.com/products/craft-design-technology-multifunctional-pen"),
    ("ugmonk-multi-pen-tray",        "Ugmonk",           "Multi Pen Tray",                   "stationery", "small", "https://ugmonk.com/products/multi-pen-tray-silver-aluminum"),
    ("hightide-penco-tape-dispenser","Hightide",         "Penco Tape Dispenser",             "stationery", "small", "https://hightidestoredtla.com/products/tape-dispenser-small-penco-green"),
    ("kokuyo-hakoake-scissors",      "KOKUYO",           "Hakoake 2-Way Scissors",           "stationery", "small", "https://www.kokuyostore.com/en_US/stationery/stationery-scissors/transparent-mechanism-hakoake-2-way-portable-scissors-white/HSM-500TM-W.html"),

    # ---- furniture ----
    ("kismas-doric-lamp-01",         "Kismas",           "Doric Lamp 01",                    "furniture",  "small", "https://kismas.com/products/doric-lamp-01"),
    ("hem-udon-chair",               "Hem",              "Udon Chair",                       "furniture",  "large", "https://hem.com/en-us/furniture/chairs-and-stools/udon/30177"),
    ("dhs-sand-teapot",              "Design House Stockholm", "Sand Teapot",                "furniture",  "small", "https://www.nordicnest.com/brands/design-house-stockholm/sand-teapot-65-cl/"),
    ("eva-solo-nordic-teapot",       "Eva Solo",         "Nordic Kitchen Teapot",            "furniture",  "small", "https://www.nordicnest.com/brands/eva-solo/nordic-kitchen-teapot/"),
    ("standard-equipment-shelving",  "Standard Equipment", "4-Tier Shelving",                "furniture",  "large", "https://www.standardequipment.ca/product/4-tier-shelving-2"),
    ("wastberg-winkel-base",         "Wästberg",         "Winkel Base W227B",                "furniture",  "small", "https://www.wastberg.com/en/products/winkel-base-w227b"),

    # ---- carry ----
    ("coteetciel-avon-backpack",     "Côte&Ciel",        "Avon Backpack",                    "carry",      "small", "https://www.coteetciel.com/products/avon-backpack-leather-black"),
    ("bellroy-key-cover",            "Bellroy",          "Key Cover",                        "carry",      "small", "https://bellroy.com/products/key-cover"),
    ("orbitkey-airtag-case",         "Orbitkey",         "Airtag Case",                      "carry",      "small", "https://www.orbitkey.eu/collections/airtag-carry/products/airtag-case"),

    # ---- apparel ----
    ("northface-thermoball-traction","The North Face",   "Thermoball Traction Boot",         "apparel",    "small", "https://www.thenorthface.com/de-de/p/schuhe-747784/thermoball-traction-winter-biwakschuhe-fur-herren-NF0A3MKH?color=KY4"),

    # ---- kitchen / gadgets (identified from the sites) ----
    ("crustmill",                    "Crust",            "P-1 / S-1 Mill",                   "tools",      "small", "https://crustmill.com/"),
    ("kal-wall",                     "Kalstore",         "Wall Calendar",                    "stationery", "small", "https://kal-store.com/products/wall"),
    ("sandbar",                      "Sandbar",          "Stream",                           "tech",       "small", "https://shop.sandbar.com/"),
]
