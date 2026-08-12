# New Product Intake — Runbook

How to add products to Well Made, end to end. **Follow this exactly next time —
do not improvise, do not re-discover the workflow.**

> ⚠️ **The #1 rule: background removal is done with the REAL Photoroom web
> tool (`https://www.photoroom.com/tools/background-remover`) driven through
> OpenTabs browser automation. NEVER use the local `rembg` model — the user
> explicitly rejected it (quality). The Photoroom API is fine while credits
> last, but the web tool is the fallback and works unlimited.**

---

## The full flow (8 steps)

```
1. Collect links        → tools/new_products.py        (manifest)
2. Fetch hero images    → tools/fetch_new.py           (staging/ raw files)
3. Review on staging    → tools/build_staging.py       (staging.html)
4. Background removal   → photoroom.com web tool via OpenTabs
                          tools/opentabs.py + tools/photoroom_cut.py
5. Publish (✓)          → in-browser GitHub API → johnyvino/fetc main
                          (or the online admin panel)
6. Update items.js      → entries written, images in assets/items/
7. Compress masters     → tools/compress_masters.py   (before committing!)
8. Commit + deploy      → single bulk commit, xqv2v0x9 identity
```

---

## Step 1 — Manifest

Edit `tools/new_products.py` — `NEW_PRODUCTS` is a list of tuples:

```python
(slug, brand, name, category, size, link)
```

- `slug`: lowercase-kebab, unique (e.g. `ugmonk-bolt-action-pen-onyx`)
- `size`: `'small'` or `'large'` (large = furniture-style bigger card)
- `category`: one of `tech / audio / watches / tools / stationery / furniture / carry / apparel`
- `link`: **cleaned** — strip `?ref=goods`, `?variant=…`, `?country=US`,
  `#fragments`, and any tracking params. Keep the base product URL.

## Step 2 — Fetch hero images

```bash
python3 tools/fetch_new.py          # downloads to tools/staging/<slug>.<ext>
```

Each product page: parse `og:image` (with `twitter:image`, JSON-LD, and
thumbnail fallbacks). Sites behind bot-blocking (e.g. The North Face/Akamai)
need a text-extraction proxy (r.jina.ai) or a direct asset-CDN grab. Verify
every download with PIL — reject social-card 1200×630 crops and tiny
thumbnails; refetch from a better source when needed.

## Step 3 — Staging review

```bash
python3 tools/build_staging.py      # writes staging.html + staging-v2.html
```

Self-contained page (inline style.css + base64 images). The user reviews
every card. **Button semantics (this is the contract):**

| Button | Meaning |
|---|---|
| **✓** | **Done** → approved, card leaves the queue |
| **🖼** | **Remove background** → cuts the image NOW via the real Photoroom web tool (local API + OpenTabs), shows the new cutout, then the card leaves the queue. If the API is unreachable it records `remove_bg` locally instead |
| **↻** | Refetch a different image (card stays) |
| **✕** | Don't include (card dims) |

Copied decisions JSON uses **`remove_bg`** (was `keep_bg`) for 🖼 cards.
Decisions persist in `localStorage` (`staging.decisions`); approved cards stay
hidden across reloads and come back with **Reset**.

### Live background removal (staging API server)

The 🖼 button POSTs to a small local server that drives the Photoroom web tab
via OpenTabs, saves the cutout to `assets/items/<slug>.png` + WebP variants,
rebuilds `staging.html`, and returns the new thumb so the card updates live:

```bash
# start it detached (survives the shell session):
python3 -c "import subprocess, sys; subprocess.Popen([sys.executable, 'tools/staging_server.py'], stdout=open('/tmp/staging-api.log','w'), stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True)"
curl -s http://127.0.0.1:8125/api/status   # {"ok": true}
```

`tools/staging_server.py` auto-finds the open Photoroom tab (opens one if
missing), prefers the **original with-bg image** from `tools/staging/` as the
cut source (falls back to the current master PNG), and is single-lock
serialized. CORS is open so `file://` staging.html can call it.

## Step 4 — Background removal (MANDATORY: Photoroom web tool via OpenTabs)

**Never rembg / local models. Use the real Photoroom web tool through
OpenTabs browser automation.**

### Prereqs

- OpenTabs MCP is running on `127.0.0.1:9515`; secret auto-read from
  `~/.opentabs/extension/auth.json` by `tools/opentabs.py`.
- One Chrome tab open on `https://www.photoroom.com/tools/background-remover`.

### The technique (why it works)

1. The tool page has a hidden `<input type="file">` whose React `onChange`
   reads `e.target.files`. Synthetic `dispatchEvent` alone does **not** fire
   React's handler — you must invoke the React prop directly:
   - set `input.files` via the native setter
     (`Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'files').set.call(input, dt.files)`)
   - find `Object.keys(input).find(k => k.startsWith('__reactProps'))` and
     call `input[k].onChange({target: input, ...})`.
2. Photoroom posts to `sdk.photoroom.com/v1/segment` with the web tool's
   embedded key + an auto-generated Cloudflare Turnstile captcha token —
   which only works inside the real browser session. That's why the API key
   extracted from the page JS can't be reused from the terminal, and why the
   whole flow must run in the user's browser.
3. **Capture the result without triggering save dialogs**: patch
   `URL.createObjectURL` in the page to `fetch()` every blob URL it creates
   and stash base64 on `window.__auto`. Also patch
   `HTMLAnchorElement.prototype.click` to no-op `blob:` hrefs so the
   "Download" button click never opens a macOS save dialog.
4. **Pull big payloads in chunks** — a single `browser_execute_script`
   response truncates around ~1 MB. Split base64 into ~120 KB slices on
   `window.__dlParts` and fetch each slice separately.
5. Verify the cutout: corners must be alpha 0 (transparent), then re-frame
   with `crop_and_square()` and emit `-800.webp`/`-1600.webp` via
   `emit_variant()` (both from `tools/process_images.py` /
   `tools/optimize_images.py`).

### Running it

```bash
# one item (id from the manifest):
python3 tools/photoroom_cut.py <slug>

# the whole remaining keep-bg set:
python3 tools/photoroom_cut.py --all
```

`tools/photoroom_cut.py` does: inject → wait for the Download button to become
enabled → click it (blob captured, no dialog) → wait for `window.__auto.b64` →
chunk-pull → verify transparent corners → save framed PNG + WebP variants to
`assets/items/<slug>.png` + `-800/-1600.webp`. Progress persists in
`tools/.pr-web-state.json` (resumable). Originals are backed up to
`tools/.bg-backup/<slug>/` before overwriting.

### Gotchas learned the hard way

- **Photoroom API quota**: the account's API key can hit
  `HTTP 402 "You have exhausted the number of images in your plan"` mid-batch
  (free tier ~10 images). Don't panic — switch to the web-tool path for the
  rest. Both produce the same result.
- **Never click the real Download in a way that opens the native save
  dialog** — it's an OS dialog no automation can accept. The anchor-click
  patch avoids it entirely.
- execute_script responses truncate on large payloads → always chunk.
- `browser_execute_script` returns double-wrapped JSON
  (`{"value":{"value": …}}`) — unwrap twice.
- OpenTabs rate-limits to 5 new sessions/min — `tools/opentabs.py` reuses one
  session (stored in `tools/.opentabs-session`); on `429` it waits 65 s.
- **Download race (fixed)**: the page creates a blob URL for the uploaded
  INPUT immediately and the Download button can be enabled before the model
  finishes — clicking early downloads the input, not the cut. The batch
  script now only accepts a capture whose byte length differs from the
  input's (it clicks Download, then watches `window.__auto.lens`).
- **Photoroom can't segment every image**: dark-on-dark scenes (e.g. the
  Ferrari Luce studio shot — car ~(4,4,4) on black) return the input
  unchanged no matter what. FIRST try a cleaner official brand-site shot
  (look for `clean` / `noback` / studio product images on the brand's CDN —
  e.g. That! Inventions had a white-background `scoop_deluxe_clean_04` that
  cut perfectly). Fallback: manual keying — the bg was uniformly
  low-luminance, so threshold alpha on `(lum <= 8) & (sat <= 10)` with a soft
  ramp, then `crop_and_square` + `emit_variant`. Always end with a full-catalog
  transparency scan:

  ```bash
  python3 - <<'EOF'
  # every master + webp must have alpha min < 128
  from PIL import Image; import os, re
  src = open('items.js', encoding='utf-8').read()
  slugs = set(re.findall(r"image: 'assets/items/([^']+)\.png'", src))
  bad = [f for s in slugs for f in (s+'.png', s+'-800.webp', s+'-1600.webp')
         if (lambda im: im.mode=='RGB' or im.convert('RGBA').getchannel('A').getextrema()[0]>=128)(Image.open('assets/items/'+f))]
  print('with background:', bad)
  EOF
  ```

  (Requires PIL; run with `tools/.venv` if system python lacks it.)

## Step 5 — Publish (bulk)

Once the batch is approved on staging, publish everything in bulk:

- **Online admin panel** (`admin.html`): Add tab, pick files, publish — same
  Git Data API flow (4-file atomic commit: `<id>.png` + `-800/-1600.webp` +
  `items.js` entry, to `johnyvino/fetc` `main`).
- **Or the agent**: `git add` the batch in this repo, commit, push — or run a
  bulk publish script.

Images are compressed for publishing — **run `tools/compress_masters.py`
before any commit** (Step 7). The site only ever renders the WebP variants
(`script.js` uses `<picture>` with `-800.webp`/`-1600.webp`), so:

- PNG masters are **capped at 1600px** (the largest size the site can show)
  and encoded as 256-color palette PNGs when smaller (alpha edges are
  preserved — PIL's FASTOCTREE keeps mid-range alpha, so cutouts stay
  anti-aliased; verified ≥38 dB PSNR composite-on-white vs original).
- WebPs stay q0.95 — they are the actual payload visitors download.
- Untracked (new) full-res masters are backed up to `tools/backup-fullres/`
  (gitignored) before compression; re-running is safe/idempotent.

Real numbers from the 2026-08 batch: **238 MB → 35 MB** (249 masters),
203 MB saved.

## Step 6 — items.js

Every product entry lives in `items.js` (`window.CURATED_DATA.items`):
`id, brand, name, category, size, image: 'assets/items/<id>.png', link,
popularity, added_on`. Keep it in sync with what's published.

## Step 7 — Commit (identity check FIRST)

When the batch is settled, commit the working tree to this repo's `main`
(`items.js`, `assets/items/*`, `tools/*`) so the dev copy matches what was
published.

> ⚠️ **Identity check — mandatory, before any commit.** The global git config
> on this machine belongs to another project (`v0x9 <puremagicdesignstudio@gmail.com>`)
> and will silently attribute Well Made commits to it. This repo's local
> identity is already set correctly (`.git/config`: `xqv2v0x9
> <xqv2v0x9@users.noreply.github.com>`). If you ever clone the repo fresh, run:
>
>     git config --local user.name  "xqv2v0x9"
>     git config --local user.email "xqv2v0x9@users.noreply.github.com"
>
> Always verify before committing:
>
>     git log --format='%h %an <%ae>' | head -3
>
> If a commit shows `puremagicdesignstudio` or `johnyvino` (this repo is NOT
> the johnyvino identity — it's xqv2v0x9), fix it before pushing.

Upload is **one shot**: everything is added in bulk locally and pushed to
GitHub as a single commit (no per-item uploads, no online admin panel for
this).

---

## Quick reference — files

| Tool | Purpose |
|---|---|
| `tools/new_products.py` | manifest of the batch |
| `tools/fetch_new.py` | fetch hero images → `tools/staging/` |
| `tools/build_staging.py` | build `staging.html` (+ embed real PNGs for publish) |
| `tools/photoroom_cut.py` | Photoroom web-tool batch (inject → capture → save) |
| `tools/opentabs.py` | MCP client for the OpenTabs browser server |
| `tools/process_images.py` | white-bg keying + crop/square framing |
| `tools/optimize_images.py` | `-800/-1600.webp` emission (q95, method 6) |
| `tools/compress_masters.py` | master compression: 1600px cap + palette PNG |
| `tools/backup-fullres/` | full-res backups of untracked masters (gitignored) |
| `tools/.bg-backup/` | originals backed up before bg removal |
| `tools/.pr-web-state.json` | per-slug success state (resume) |
