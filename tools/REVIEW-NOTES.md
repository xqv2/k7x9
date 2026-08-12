# Review notes — batch 1–3 (95 products)

Flow (per user, Aug 2026):
1. Images for new products come from `shop.uncrate.com` (easy to grab); links point
   to the brand's own product page.
2. Review on `staging.html` with 4 buttons:
   - **✓ done**  — approved, good to go
   - **🖼 remove background** — "cut" the image (real Photoroom web tool via
     OpenTabs; the staging page's 🖼 calls `tools/staging_server.py` to cut live)
   - **↻ refetch** — get a different image
   - **✕ remove** — don't include the product
3. After the user posts decisions, apply them and rebuild staging to show only
   what still needs attention.

## Cutting
"Cutting" = background removal: taking the product photo and making the
background transparent (Photoroom). Master = `assets/items/<slug>.png`
(transparent cutout), variants = `-800.webp` / `-1600.webp`.

## IMPORTANT — the 🖼 button is DECISION-ONLY
Clicking 🖼 on staging must NEVER start cutting — it only records the
`remove_bg` decision. The agent does the actual Photoroom cuts AFTER the user
finishes reviewing (via `tools/photoroom_cut.py`). The user was explicit:
"i am gonna make a decision first then you do your things".

## Review #4 — user approved all 38 cut products (review complete)
approved = the 38 cut products (bell-bullitt-helmet ... pinned-sound-stick),
remove_bg = [], redo = [], removed = []. ALL 95 decided: 87 approved, 8 removed.

## Image compression — TinyPNG API (not local PIL)
User: "use tiny png for all the new images we are uploading". The 87 NEW-batch
masters only (NOT the 139 original-site ones). `tools/tinify_compress.py`:
POST each PNG to api.tinify.com/shrink (key in tools/.tinify-key, gitignored),
GET the result, save over the master; resumable via tools/.tinify-progress.json.
Result: 54.0MB -> 21.9MB (59% smaller), all readable, alpha preserved,
dimensions unchanged. 87 compressions used of 500 free monthly credits.
NEVER commit tools/.tinify-key.

## Review #3 decision set (user-posted JSON, saved verbatim)
approved: fellow-tally-pro, casio-moonphase
remove_bg (38): bell-bullitt-helmet, vigo-edison-faucet, panisa-chess-set,
trmnl-og, marcellin-pizza-axe, marcellin-knife-trio, marcellin-ulu-knife,
marcellin-grill-press, dotti-super-scrubber, blackcreek-rolling-pin,
schmidt-zebra-wood-set, schmidt-shears, atech-multitool-pen, cwandt-pen-type-a,
craighill-eyewear-stand, craighill-perch-bookmark, craighill-kepler-pen,
ratio-six, finex-skillet, alessi-9091-kettle, balmuda-toaster-pro,
balmuda-teppanyaki, balmuda-the-clock, balmuda-naturewind, balmuda-the-speaker,
porsche-design-carving-set, porsche-design-universal-knife,
porsche-design-steak-knives, hegid-celeste, bell-ross-wayne,
story-of-porsche-book, churchill-wit-wisdom, james-bond-style-book,
latelierduvin-soft-machine, latelierduvin-oeno, keysmart-rugged,
astroflex-chelsea-boot, pinned-sound-stick
removed: barebones-flatware, balmuda-moonkettle, thatinventions-scoopthat

## Review #2 decision set (user-posted JSON, saved verbatim)

approved (done — do not show again):
rocco-super-smart-fridge, wastberg-winkel-base, bellroy-key-cover,
orbitkey-airtag-case, aulumu-battery-pack, satechi-headphone-stand,
twemco-bq-17, transparent-turntable, tid-no-1, veark-sk15-santoku,
serax-bottle-opener, ugmonk-analog-weekly-kit, ugmonk-bolt-action-pen-onyx,
ugmonk-craft-pen, ugmonk-multi-pen-tray, hightide-penco-tape-dispenser,
kokuyo-hakoake-scissors, kismas-doric-lamp-01, hem-udon-chair, dhs-sand-teapot,
eva-solo-nordic-teapot, standard-equipment-shelving, coteetciel-avon-backpack,
sandbar, xbloom-original, aarke-carbonator-3, breitling-chronomat-b01-42,
steamerystockholm-lint-brush, bell-ross-br05, hoto-air-capsule, combo-ski,
nike-hyperice-hyperboot, grau-salt-lamp, fsb-door-handle-1138,
jamesbrand-the-palmer

remove_bg (need CUTTING — shown again on staging):
jamesbrand-the-carter, craighill-desk-knife, craighill-temple-flashlight,
stelton-chefs-knife, om-aero-pickleball, titleist-t100, advance-paris-a12,
stelton-time-clock

redo: (none)

removed (delete from catalog):
zellerfeld-mars-mellow

## Staging state (after review #4 — ALL 95 DECIDED)
- approved: 49 (35 + 12 + 2)
- removed: 8 (zellerfeld, craighill-desk-knife, stelton-chefs-knife,
  aj-bankers-clock, steelport-bread-knife, barebones-flatware,
  balmuda-moonkettle, thatinventions-scoopthat) — deleted from `items.js` + files
- cut queue: 38 — **ALL CUT via the real Photoroom web tool** (user said
  "Go"; `tools/cut_queue.py` + `tools/staging_server.cut_slug`, 2026-08-11):
  38/38 OK, 0 failed, all masters + WebP variants regenerated and verified
  transparent, nothing corrupt. Then ALL 38 approved by user (review #4).
- undecided: 0
Catalog now: **225 products** (was 233, minus 8 removed), no missing files.
87 new-batch masters TinyPNG-compressed (54.0 -> 21.9MB).
