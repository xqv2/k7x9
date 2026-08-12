# New Product Intake — Runbook

How to add products to Well Made, end to end. **Follow this exactly next time —
do not improvise, do not re-discover the workflow.**

> ⚠️ **The #1 rule: background removal is done with the REAL Photoroom web
> tool (`https://www.photoroom.com/tools/background-remover`) driven through
> OpenTabs browser automation. NEVER use the local `rembg` model — the user
> explicitly rejected it (quality). The Photoroom API is fine while credits
> last, but the web tool is the fallback and works unlimited.**

---

## The full flow (7 steps)

```
1. Collect links        → tools/new_products.py        (manifest)
2. Fetch hero images    → tools/fetch_new.py           (staging/ raw files)
3. Review on staging    → tools/build_staging.py       (staging.html)
4. Background removal   → photoroom.com web tool via OpenTabs
                          tools/opentabs.py + tools/pr_web_batch.py
5. Publish (✓)          → in-browser GitHub API → johnyvino/fetc main
                          (or the online admin panel)
6. Update items.js      → entries written, images in assets/items/
7. Commit + deploy
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
| **✓** | Approve → **removes the card from the staging queue** (it's done) |
| **🖼** | Approve as-is → also removes the card |
| **↻** | Refetch a different image (card stays) |
| **✕** | Don't include (card dims) |

**No direct publishing from staging.** The staging page is review-only: ✓ / 🖼
move the product out of the queue. Publishing happens **in bulk** afterwards —
via the online admin panel, or the agent commits/pushes the batch (Step 7).
Decisions persist in `localStorage` (`staging.decisions`); approved cards stay
hidden across reloads and come back with **Reset**.

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
python3 tools/pr_web_batch.py <slug>

# the whole remaining keep-bg set:
python3 tools/pr_web_batch.py --all
```

`tools/pr_web_batch.py` does: inject → wait for the Download button to become
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

## Step 5 — Publish (bulk)

Once the batch is approved on staging, publish everything in bulk:

- **Online admin panel** (`admin.html`): Add tab, pick files, publish — same
  Git Data API flow (4-file atomic commit: `<id>.png` + `-800/-1600.webp` +
  `items.js` entry, to `johnyvino/fetc` `main`).
- **Or the agent**: `git add` the batch in this repo, commit, push — or run a
  bulk publish script.

Images are already compressed for publishing: the site only ever renders the
WebP variants (`script.js` uses `<picture>` with `-800.webp`/`-1600.webp`), so
the PNG master is capped at 1600px and the WebPs are q0.95 — no huge uploads.

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
| `tools/pr_web_batch.py` | Photoroom web-tool batch (inject → capture → save) |
| `tools/opentabs.py` | MCP client for the OpenTabs browser server |
| `tools/process_images.py` | white-bg keying + crop/square framing |
| `tools/optimize_images.py` | `-800/-1600.webp` emission (q95, method 6) |
| `tools/.bg-backup/` | originals backed up before bg removal |
| `tools/.pr-web-state.json` | per-slug success state (resume) |
