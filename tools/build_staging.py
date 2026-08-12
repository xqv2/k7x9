#!/usr/bin/env python3
"""
Build a self-contained staging page for the new-product batch.

The page renders new products EXACTLY like the real site (inline style.css,
same .card markup), plus per-card "good / redo" icon buttons and a toolbar
with counts, copy-decisions, and reset. Images are embedded as data URIs
(two sizes: card + full-size for a click-to-inspect lightbox), so the file
works anywhere with no server.

Decisions are persisted in localStorage (key: staging.decisions), keyed by
slug, so rebuilding the page never loses your picks.

Usage (from project root):
    python3 tools/build_staging.py
"""

import base64
import datetime as _dt
import io
import json
import os
import re
import sys
from html import escape

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from new_products import NEW_PRODUCTS  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
STAGING = os.path.join(HERE, "staging")

# Cards that visibly changed vs the original batch:
#  bg -> background removed (real Photoroom)   img -> brand-new image
BG_REMOVED = {"xbloom-original", "aarke-carbonator-3", "breitling-chronomat-b01-42", "steamerystockholm-lint-brush",
              "aulumu-battery-pack", "satechi-headphone-stand", "rocco-super-smart-fridge", "twemco-bq-17",
              "aiaiai-tma-2", "transparent-turntable", "tid-no-1", "veark-sk15-santoku", "serax-bottle-opener",
              "ugmonk-analog-weekly-kit", "ugmonk-bolt-action-pen-onyx", "ugmonk-craft-pen",
              "ugmonk-multi-pen-tray", "hightide-penco-tape-dispenser", "kokuyo-hakoake-scissors",
              "kismas-doric-lamp-01", "hem-udon-chair", "dhs-sand-teapot", "eva-solo-nordic-teapot",
              "standard-equipment-shelving", "wastberg-winkel-base", "coteetciel-avon-backpack",
              "bellroy-key-cover", "orbitkey-airtag-case", "northface-thermoball-traction", "crustmill",
              "kal-wall"}
NEW_IMAGE = {"rocco-super-smart-fridge", "aiaiai-tma-2", "wastberg-winkel-base", "bellroy-key-cover",
             "orbitkey-airtag-case", "northface-thermoball-traction", "crustmill"}
OUT = os.path.join(ROOT, "staging.html")
OUT_V2 = os.path.join(ROOT, "staging-v2.html")  # fresh filename defeats any cache

THUMB_LONG = 640
FULL_LONG = 1600
# Published master PNG is capped at the largest size the site ever displays
# (script.js renders -800/-1600.webp only), so uploads stay small.
PNG_LONG = 1600
JPEG_Q = 82
ADDED_ON_DEFAULT = _dt.date.today().isoformat()


def load_style():
    with open(os.path.join(ROOT, "style.css"), encoding="utf-8") as f:
        return f.read()


def find_staging_file(slug):
    # Prefer the final processed PNG (bg removed / installed) if it exists,
    # so approved cards show exactly what will be published.
    final = os.path.join(ROOT, "assets", "items", slug + ".png")
    if os.path.exists(final):
        return final
    if not os.path.isdir(STAGING):
        return None
    for f in sorted(os.listdir(STAGING)):
        base, ext = os.path.splitext(f)
        if base == slug and ext.lower() in (".jpg", ".jpeg", ".png", ".webp", ".avif"):
            return os.path.join(STAGING, f)
    return None


def to_data_uri(img, long_edge):
    """Downscale to long_edge (max), return a data URI. PNG if source had
    alpha, else JPEG (white flattened)."""
    img = img.convert("RGBA")
    w, h = img.size
    long_side = max(w, h)
    if long_side > long_edge:
        ratio = long_edge / long_side
        img = img.resize((max(1, round(w * ratio)), max(1, round(h * ratio))), Image.LANCZOS)
    buf = io.BytesIO()
    # Keep PNG only when there is meaningful transparency.
    has_alpha = img.getchannel("A").getextrema()[0] < 250
    if has_alpha:
        img.save(buf, "PNG", optimize=True)
        mime = "image/png"
    else:
        img.convert("RGB").save(buf, "JPEG", quality=JPEG_Q, optimize=True)
        mime = "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def to_png_data_uri(path, long_edge):
    """Full-quality PNG data URI (downscaled to long_edge max). This is what
    gets uploaded when the ✓ button publishes the item to the site repo."""
    img = Image.open(path).convert("RGBA")
    w, h = img.size
    if max(w, h) > long_edge:
        ratio = long_edge / max(w, h)
        img = img.resize((max(1, round(w * ratio)), max(1, round(h * ratio))), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def item_meta(slug, default_popularity=70):
    """Pull popularity / added_on from the local items.js entry, so the
    published entry matches the catalog exactly."""
    try:
        src = open(os.path.join(ROOT, "items.js"), encoding="utf-8").read()
        for line in src.splitlines():
            if f"id: '{slug}'" in line or f'id: "{slug}"' in line:
                pop = re.search(r"popularity:\s*(\d+)", line)
                add = re.search(r"added_on:\s*'([^']+)'", line)
                return {
                    "popularity": int(pop.group(1)) if pop else default_popularity,
                    "added_on": add.group(1) if add else _dt.date.today().isoformat(),
                }
    except OSError:
        pass
    return {"popularity": default_popularity, "added_on": _dt.date.today().isoformat()}


def main():
    items = []
    missing = []
    for slug, brand, name, category, size, link in NEW_PRODUCTS:
        src = find_staging_file(slug)
        if not src:
            missing.append(slug)
            print(f"  MISSING {slug}")
            continue
        img = Image.open(src)
        meta = item_meta(slug)
        png_path = os.path.join(ROOT, "assets", "items", slug + ".png")
        png_uri = to_png_data_uri(png_path, PNG_LONG) if os.path.exists(png_path) else ""
        items.append({
            "slug": slug,
            "brand": brand,
            "name": name,
            "category": category,
            "size": size,
            "link": link,
            "image": f"assets/items/{slug}.png",
            "popularity": meta["popularity"],
            "added_on": meta["added_on"],
            "thumb": to_data_uri(img, THUMB_LONG),
            "png": png_uri,
            "flag": "bg" if slug in BG_REMOVED else ("img" if slug in NEW_IMAGE else ""),
        })
        print(f"  ok     {slug}")

    if missing:
        print(f"\nMissing images (skipped): {missing}")

    style = load_style()
    data_json = json.dumps(items)
    html = template(style, data_json)
    for path in (OUT, OUT_V2):
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
    print(f"\nWrote {OUT} + {os.path.basename(OUT_V2)} ({os.path.getsize(OUT) // 1024} kB, {len(items)} products)")


BUILD_STAMP = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")


BG_N = len(BG_REMOVED)
IMG_N = len(NEW_IMAGE)


def template(style, data_json):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="robots" content="noindex, nofollow">
<meta http-equiv="Cache-Control" content="no-store, no-cache, must-revalidate">
<meta http-equiv="Pragma" content="no-cache">
<meta http-equiv="Expires" content="0">
<title>Staging · Well Made — new batch</title>
<style>
{style}

/* ---- staging-only additions ---- */
.staging-toolbar {{
    display: flex; align-items: center; gap: 14px; flex-wrap: wrap;
    padding: 12px var(--side-pad);
    background: #fff; border-bottom: 1px solid var(--line, #e5e5e5);
    position: sticky; top: 0; z-index: 20;
}}
.staging-toolbar-title {{ font-size: 14px; font-weight: 600; letter-spacing: 0.02em; }}
.staging-build {{ font-weight: 400; color: var(--muted); font-size: 12px; }}
.staging-toolbar-note {{ font-size: 12px; color: var(--muted); }}
.staging-legend {{ display: flex; gap: 12px; font-size: 12px; }}
.staging-legend .lg {{ display: inline-flex; align-items: center; gap: 4px; }}
.lg-bg  {{ color: #2e7d32; }}
.lg-img {{ color: #1565c0; }}
.staging-count {{ font-size: 13px; font-variant-numeric: tabular-nums; }}
.staging-count b {{ font-weight: 600; }}
.staging-count .good   {{ color: #2e7d32; }}
.staging-count .bg     {{ color: #1565c0; }}
.staging-count .redo   {{ color: #c62828; }}
.staging-count .remove {{ color: #546e7a; }}
.staging-toolbar .spacer {{ flex: 1; }}
.staging-toolbtn {{
    font: inherit; font-size: 12px; letter-spacing: 0.04em;
    padding: 7px 14px; border-radius: 999px; cursor: pointer;
    border: 1px solid #d0d0d0; background: #fff; color: #333;
    transition: border-color .15s, color .15s, background .15s;
}}
.staging-toolbtn:hover {{ border-color: #999; }}
.staging-toolbtn.reset:hover {{ border-color: #c62828; color: #c62828; }}

.card {{ position: relative; }}
.staging-controls {{
    position: absolute; top: 10px; right: 10px; z-index: 5;
    display: flex; gap: 8px;
}}
.staging-btn {{
    width: 34px; height: 34px; border-radius: 50%;
    border: 1px solid rgba(0,0,0,.12);
    background: rgba(255,255,255,.92);
    box-shadow: 0 1px 4px rgba(0,0,0,.14);
    cursor: pointer; font-size: 16px; line-height: 1;
    display: inline-flex; align-items: center; justify-content: center;
    transition: transform .12s, background .12s, color .12s, border-color .12s;
}}
.staging-btn:hover {{ transform: scale(1.08); }}
.staging-btn.good   {{ color: #2e7d32; }}
.staging-btn.bg     {{ color: #1565c0; }}
.staging-btn.redo   {{ color: #b23b2e; }}
.staging-btn.remove {{ color: #546e7a; }}
.staging-btn.is-on.good   {{ background: #2e7d32; border-color: #2e7d32; color: #fff; }}
.staging-btn.is-on.bg     {{ background: #1565c0; border-color: #1565c0; color: #fff; }}
.staging-btn.is-on.redo   {{ background: #b23b2e; border-color: #b23b2e; color: #fff; }}
.staging-btn.is-on.remove {{ background: #546e7a; border-color: #546e7a; color: #fff; }}

.card.is-good   {{ outline: 2px solid #2e7d32; outline-offset: -2px; }}
.card.is-bg     {{ outline: 2px solid #1565c0; outline-offset: -2px; }}
.card.is-redo   {{ outline: 2px solid #b23b2e; outline-offset: -2px; }}
.card.is-remove {{ opacity: .45; outline: 2px dashed #78909c; outline-offset: -2px; }}

.staging-badge {{
    position: absolute; top: 10px; left: 10px; z-index: 5;
    font-size: 10px; letter-spacing: .12em; text-transform: uppercase;
    padding: 3px 8px; border-radius: 999px; color: #fff; font-weight: 600;
}}
.staging-badge.good   {{ background: #2e7d32; }}
.staging-badge.bg     {{ background: #1565c0; }}
.staging-badge.redo   {{ background: #b23b2e; }}
.staging-badge.remove {{ background: #546e7a; }}

.staging-category {{ position: absolute; bottom: 10px; right: 10px; z-index: 5;
    font-size: 10px; letter-spacing: .12em; text-transform: uppercase;
    padding: 3px 8px; border-radius: 999px;
    background: rgba(255,255,255,.88); color: rgba(10,10,10,.55);
    border: 1px solid rgba(0,0,0,.08);
}}

.staging-update {{
    position: absolute; bottom: 10px; left: 10px; z-index: 5;
    font-size: 10px; letter-spacing: .1em; text-transform: uppercase; font-weight: 700;
    padding: 3px 8px; border-radius: 999px; color: #fff;
}}
.staging-update.is-bg  {{ background: #2e7d32; }}
.staging-update.is-img {{ background: #1565c0; }}

/* Lightbox */
.staging-lightbox {{
    position: fixed; inset: 0; z-index: 50; display: none;
    background: rgba(0,0,0,.82);
    align-items: center; justify-content: center; cursor: zoom-out;
    padding: 5vh 4vw;
}}
.staging-lightbox.open {{ display: flex; }}
.staging-lightbox img {{ max-width: 100%; max-height: 90vh; object-fit: contain;
    border-radius: 4px; background: #fff; }}
.staging-lightbox-cap {{
    position: fixed; bottom: 18px; left: 50%; transform: translateX(-50%);
    color: #fff; font-size: 13px; background: rgba(0,0,0,.55);
    padding: 6px 14px; border-radius: 999px; white-space: nowrap;
}}

body.staging-scroll-lock {{ overflow: hidden; }}

.card.is-approved {{ outline: 2px solid #2e7d32; outline-offset: -2px; }}
</style>
</head>
<body>
<header class="site-header">
    <h1 class="site-title">Well Made</h1>
    <p class="site-subtitle">Staging — reviewing <b id="stgTotal"></b> new products before they hit the catalog.</p>
</header>

<div class="staging-toolbar" id="stgToolbar">
    <span class="staging-toolbar-title">New batch <span class="staging-build">· build {BUILD_STAMP}</span></span>
    <span class="staging-legend">
        <span class="lg lg-bg">◉ bg removed ({BG_N})</span>
        <span class="lg lg-img">◉ new image ({IMG_N})</span>
    </span>
    <span class="staging-count">
        <b class="good" id="stgGood">0</b> good ·
        <b class="bg" id="stgBg">0</b> keep bg ·
        <b class="redo" id="stgRedo">0</b> redo ·
        <b class="remove" id="stgRemove">0</b> remove ·
        <span id="stgPending">0</span> undecided
    </span>
    <span class="staging-toolbar-note"><b>✓</b> / <b>🖼</b> approve &amp; remove from staging (publish in bulk later) · <b>↻</b> refetch · <b>✕</b> don't include. Click a photo to zoom.</span>
    <span class="spacer"></span>
    <button type="button" class="staging-toolbtn" id="stgCopy">Copy decisions</button>
    <button type="button" class="staging-toolbtn reset" id="stgReset">Reset</button>
</div>

<nav class="filter-bar" aria-label="Categories">
    <div class="filter-list" id="filterList"></div>
</nav>

<main class="grid" id="grid"></main>

<footer class="site-footer">
    <small class="footer-copy">Staging build — ✓ / 🖼 approve and remove from the queue; publishing happens in bulk (admin panel or git).</small>
</footer>

<div class="staging-lightbox" id="lightbox" role="dialog" aria-modal="true">
    <img id="lightboxImg" alt="">
    <div class="staging-lightbox-cap" id="lightboxCap"></div>
</div>



<script>
(function () {{
    'use strict';
    const ITEMS = {data_json};
    const LS_KEY = 'staging.decisions';
    const grid = document.getElementById('grid');
    const filterList = document.getElementById('filterList');
    const lightbox = document.getElementById('lightbox');
    const lightboxImg = document.getElementById('lightboxImg');
    const lightboxCap = document.getElementById('lightboxCap');

    let decisions = {{}};
    try {{ decisions = JSON.parse(localStorage.getItem(LS_KEY)) || {{}}; }} catch (e) {{}}
    let activeCat = 'all';

    // Approved = ✓ / 🖼 decision; those cards leave the staging queue.
    // (Publishing happens in bulk via the admin panel / git, not from here.)
    const isApproved = (slug) => decisions[slug] === 'good' || decisions[slug] === 'bg';

    const escapeHtml = (s) => String(s)
        .replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;').replaceAll("'", '&#39;');

    const cats = ['all', ...new Set(ITEMS.map(i => i.category))];

    function renderFilters() {{
        filterList.innerHTML = cats.map(c => {{
            const count = c === 'all' ? ITEMS.length : ITEMS.filter(i => i.category === c).length;
            return `<button class="filter-link${{c === activeCat ? ' active' : ''}}" type="button" data-cat="${{c}}">${{c}} (${{count}})</button>`;
        }}).join('');
    }}

    function decisionOf(slug) {{ return decisions[slug] || ''; }}

    function renderGrid() {{
        // approved (✓ / 🖼) cards leave the staging queue
        const base = ITEMS.filter(i => !isApproved(i.slug));
        const visible = activeCat === 'all' ? base : base.filter(i => i.category === activeCat);
        grid.innerHTML = visible.map(item => {{
            const d = decisionOf(item.slug);
            const query = item.brand ? `${{item.brand}} ${{item.name}}` : item.name;
            const url = item.link || `https://www.google.com/search?q=${{encodeURIComponent(query)}}`;
            const flags = [];
            if (item.size === 'large') flags.push('large');
            const cardCls = ['card', item.size].join(' ');
            const stateCls = d === 'good' ? ' is-good' : (d === 'bg' ? ' is-bg' : (d === 'redo' ? ' is-redo' : (d === 'remove' ? ' is-remove' : '')));
            return `
            <div class="${{cardCls}}${{stateCls}}"
                 data-slug="${{item.slug}}" data-category="${{item.category}}">
                <a class="card-link" href="${{escapeHtml(url)}}" target="_blank" rel="noopener noreferrer">
                    <div class="card-image has-image">
                        <span class="card-image-fallback">${{escapeHtml(item.brand || item.name)}}</span>
                        <img src="${{item.thumb}}" alt="${{escapeHtml(query)}}" loading="lazy" data-full="${{item.png || item.full || item.thumb}}">
                    </div>
                </a>
                <div class="card-meta">
                    <a class="card-link card-text-link" href="${{escapeHtml(url)}}" target="_blank" rel="noopener noreferrer">
                        <span class="card-name">${{escapeHtml(item.name)}}</span>
                        <span class="card-brand">${{escapeHtml(item.brand || '')}}</span>
                    </a>
                </div>
                <span class="staging-badge ${{d}}" data-badge hidden>${{d === 'good' ? 'good' : (d === 'bg' ? 'keep bg' : (d === 'redo' ? 'redo' : 'remove'))}}</span>
                <span class="staging-category">${{item.category}}</span>
                ${{item.flag ? `<span class="staging-update is-${{item.flag}}">${{item.flag === 'bg' ? 'bg removed' : 'new image'}}</span>` : ''}}
                <div class="staging-controls">
                    <button type="button" class="staging-btn good${{d === 'good' ? ' is-on' : ''}}"
                            data-act="good" title="Good — remove background & process" aria-label="Good — remove background & process">✓</button>
                    <button type="button" class="staging-btn bg${{d === 'bg' ? ' is-on' : ''}}"
                            data-act="bg" title="Keep background — use photo as-is" aria-label="Keep background — use photo as-is">
                        <svg viewBox="0 0 16 16" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.4" aria-hidden="true">
                            <rect x="2" y="3.5" width="12" height="9" rx="1.2"/>
                            <circle cx="5.8" cy="7" r="1.1"/>
                            <path d="M2 11.5l3.6-3.2 2.6 2.4 2.8-2.6 2.8 2.6"/>
                        </svg>
                    </button>
                    <button type="button" class="staging-btn redo${{d === 'redo' ? ' is-on' : ''}}"
                            data-act="redo" title="Redo — refetch image" aria-label="Redo — refetch image">↻</button>
                    <button type="button" class="staging-btn remove${{d === 'remove' ? ' is-on' : ''}}"
                            data-act="remove" title="Remove — don't include this product" aria-label="Remove — don't include this product">✕</button>
                </div>
            </div>`;
        }}).join('');
    }}

    function persist() {{
        localStorage.setItem(LS_KEY, JSON.stringify(decisions));
        const good = ITEMS.filter(i => decisions[i.slug] === 'good').length;
        const bg = ITEMS.filter(i => decisions[i.slug] === 'bg').length;
        const redo = ITEMS.filter(i => decisions[i.slug] === 'redo').length;
        const remove = ITEMS.filter(i => decisions[i.slug] === 'remove').length;
        document.getElementById('stgGood').textContent = good;
        document.getElementById('stgBg').textContent = bg;
        document.getElementById('stgRedo').textContent = redo;
        document.getElementById('stgRemove').textContent = remove;
        document.getElementById('stgPending').textContent = ITEMS.length - good - bg - redo - remove;
    }}

    function setDecision(slug, act) {{
        decisions[slug] = (decisions[slug] === act) ? null : act;
        if (!decisions[slug]) delete decisions[slug];
        persist();
        renderGrid();
    }}

    grid.addEventListener('click', (e) => {{
        const btn = e.target.closest('.staging-btn');
        if (btn) {{
            e.preventDefault(); e.stopPropagation();
            const card = btn.closest('.card');
            const slug = card.dataset.slug;
            const act = btn.dataset.act;
            // ✓ / 🖼 approve: the card leaves the queue (renderGrid filters it)
            setDecision(slug, act);
            return;
        }}
        const img = e.target.closest('.card-image img');
        if (img) {{
            e.preventDefault(); e.stopPropagation();
            lightboxImg.src = img.dataset.full || img.src;
            lightboxCap.textContent = img.alt;
            lightbox.classList.add('open');
            document.body.classList.add('staging-scroll-lock');
        }}
    }});

    lightbox.addEventListener('click', () => {{
        lightbox.classList.remove('open');
        document.body.classList.remove('staging-scroll-lock');
    }});
    document.addEventListener('keydown', (e) => {{
        if (e.key === 'Escape') {{
            lightbox.classList.remove('open');
            document.body.classList.remove('staging-scroll-lock');
        }}
    }});

    filterList.addEventListener('click', (e) => {{
        const btn = e.target.closest('.filter-link');
        if (!btn) return;
        activeCat = btn.dataset.cat;
        renderFilters();
        renderGrid();
    }});

    document.getElementById('stgCopy').addEventListener('click', async () => {{
        const out = {{
            approved: ITEMS.filter(i => decisions[i.slug] === 'good').map(i => i.slug),
            keep_bg: ITEMS.filter(i => decisions[i.slug] === 'bg').map(i => i.slug),
            redo: ITEMS.filter(i => decisions[i.slug] === 'redo').map(i => i.slug),
            removed: ITEMS.filter(i => decisions[i.slug] === 'remove').map(i => i.slug),
        }};
        const text = JSON.stringify(out, null, 2);
        try {{
            await navigator.clipboard.writeText(text);
            document.getElementById('stgCopy').textContent = 'Copied ✓';
        }} catch (err) {{
            const ta = document.createElement('textarea');
            ta.value = text; ta.style.position = 'fixed'; ta.style.opacity = '0';
            document.body.appendChild(ta); ta.select();
            try {{ document.execCommand('copy'); }} catch (e2) {{}}
            ta.remove();
            document.getElementById('stgCopy').textContent = 'Copied ✓';
        }}
        setTimeout(() => document.getElementById('stgCopy').textContent = 'Copy decisions', 1200);
    }});

    document.getElementById('stgReset').addEventListener('click', () => {{
        if (!confirm('Reset ALL staging decisions?')) return;
        decisions = {{}};
        localStorage.removeItem(LS_KEY);
        persist();
        renderGrid();
    }});

    document.getElementById('stgTotal').textContent = ITEMS.length;
    renderFilters();
    renderGrid();
    persist();
}})();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
