# tools/ — product pipeline

Internal tooling for the curated catalog. Nothing here is shipped; the site only
uses `../assets/` and `../items.js`.

## Layout

| Path | Purpose |
| --- | --- |
| `build_staging.py` | Builds `staging.html` from `items.js` + `assets/` for the review flow (✓ done / 🖼 mark for cut / ↻ refetch / ✕ remove). Run after any catalog change. |
| `staging_server.py` | Small local API (port 8125) that drives a live Photoroom cut via the user's browser tab. Only needed for the old click-to-cut flow; the review flow now marks decisions and cuts later. |
| `photoroom_cut.py` | **Background removal via the real Photoroom web tool** (OpenTabs → user's browser tab, never a local model). Resumable: `python3 photoroom_cut.py <id> [<id> ...]` or `--all`. |
| `cut_queue.py` | Batches all `needs cut` products through `photoroom_cut.py`. |
| `tinify_compress.py` | TinyPNG API compression for new-batch masters (key in `tools/.tinify-key`, gitignored). Resumable. |
| `compress_masters.py` / `optimize_images.py` / `process_images.py` | Older local image resize/optimize helpers (superseded by TinyPNG for new batches). |
| `fetch_new.py` / `new_products.py` | Scrape/assemble new product entries (canonical links + images). |
| `opentabs.py` | Thin client for the OpenTabs MCP server (drives the user's browser tabs). |
| `decisions.json` | Latest review decisions from staging (`approved` / `remove_bg` / `redo` / `removed`). |
| `REVIEW-NOTES.md` | Working notes + process rules for the review/cut flow. |
| `PROCESS.md` | The full runbook (fetch → review → cut → compress → publish). |
| `staging/` | Original with-background sources per product (cut inputs). |
| `backup-fullres/` | Full-resolution backups of removed/replaced products. |
| `archive/` | One-off / superseded scripts kept for reference — not part of the active flow. |

## Common commands

```bash
# Rebuild the review page
python3 tools/build_staging.py

# Cut backgrounds for specific products (or all queued)
python3 tools/photoroom_cut.py <id> [<id> ...]
python3 tools/photoroom_cut.py --all

# Compress the new-batch masters via TinyPNG
python3 tools/tinify_compress.py

# Serve the staging API (live-cut flow only)
python3 tools/staging_server.py   # http://127.0.0.1:8125
```

## Golden rules (from painful experience)

1. **Review first, cut after** — the staging buttons only *record* decisions;
   the actual Photoroom cut happens only when the user says go.
2. **Always use the real Photoroom web tool** for background removal — never a
   local model. Images the tool can't segment (dark-on-black) get a manual
   luminance key, documented in `PROCESS.md`.
3. **One bulk commit, identity `xqv2v0x9`** — never johnyvino. Push via SSH key
   `k7x9-local` (repo remote is already wired; the other GitHub account is
   untouched).
4. After any cut/compress pass, run the full transparency + missing-file scan
   (see `PROCESS.md`).
