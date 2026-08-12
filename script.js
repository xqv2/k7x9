(function () {
    'use strict';

    const data = window.CURATED_DATA;
    if (!data) return;

    const grid       = document.getElementById('grid');
    const filterList = document.getElementById('filterList');
    const countEl    = document.getElementById('productCount');
    const validCats  = new Set(data.categories.map(c => c.id));

    const escape = (s) => String(s)
        .replaceAll('&',  '&amp;')
        .replaceAll('<',  '&lt;')
        .replaceAll('>',  '&gt;')
        .replaceAll('"',  '&quot;')
        .replaceAll("'",  '&#39;');

    const parseHash = () => {
        const raw = (location.hash || '').slice(1);
        const m = raw.match(/(?:^|[?&])w=([A-Za-z0-9,\-]+)/);
        const cat = raw.split(/[?&]/)[0];
        return {
            cat: validCats.has(cat) ? cat : 'all',
            wishlist: cat === 'wishlist',
            shared: m ? m[1].split(',').filter(Boolean) : null,
        };
    };

    // No two items of the same category appear within `window` positions,
    // so a category never repeats within one row of the 4-col grid.
    function shuffleMixed(arr, window = 4) {
        const remaining = arr.slice();
        const out = [];
        while (remaining.length) {
            const recent = new Set(out.slice(-window).map(i => i.category));
            const eligible = [];
            for (let i = 0; i < remaining.length; i++) {
                if (!recent.has(remaining[i].category)) eligible.push(i);
            }
            const pool = eligible.length ? eligible : remaining.map((_, i) => i);
            const idx = pool[Math.floor(Math.random() * pool.length)];
            out.push(remaining.splice(idx, 1)[0]);
        }
        return out;
    }

    function legacyCopy(text) {
        const ta = document.createElement('textarea');
        ta.value = text;
        ta.setAttribute('readonly', '');
        ta.style.cssText = 'position:fixed;opacity:0;pointer-events:none;';
        document.body.appendChild(ta);
        ta.select();
        try { document.execCommand('copy'); } catch {}
        ta.remove();
    }

    function copyToClipboard(text, onDone) {
        if (navigator.clipboard?.writeText) {
            navigator.clipboard.writeText(text).then(onDone).catch(() => {
                legacyCopy(text);
                onDone();
            });
        } else {
            legacyCopy(text);
            onDone();
        }
    }

    const items = shuffleMixed(data.items);

    // --- Wishlist: localStorage picks + shareable #w=id1,id2 hash ---
    const WL_KEY = 'wellmade.wishlist.v1';
    const readWishlist = () => {
        try {
            const v = JSON.parse(localStorage.getItem(WL_KEY) || '[]');
            return Array.isArray(v) ? v : [];
        } catch { return []; }
    };
    const persistWishlist = () =>
        localStorage.setItem(WL_KEY, JSON.stringify([...wishlist]));

    let wishlist         = new Set(readWishlist());
    let wishFilterActive = false;
    let sharedIds        = null;
    let openSharePop     = null;
    let updateWishCta    = null;
    let activeCategory   = 'all';

    const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches || false;

    const applyHash = () => {
        const h = parseHash();
        activeCategory = h.cat;
        sharedIds      = h.shared;
        // #wishlist is a pseudo-category: restore the wishlist filter view.
        wishFilterActive = h.wishlist && wishlist.size > 0;
    };
    applyHash();

    function renderFilters() {
        // Tabs are mutually exclusive — when the wishlist filter is on, no
        // category tab is highlighted (only the ♥ chip).
        const all = [{ id: 'all', label: 'all' }, ...data.categories];
        const cats = all.map(c => {
            const cls = !wishFilterActive && c.id === activeCategory ? 'filter-link active' : 'filter-link';
            return `<button class="${cls}" type="button" data-cat="${escape(c.id)}">${escape(c.label)}</button>`;
        }).join('');
        const chip = `<button class="filter-link wish-filter${wishFilterActive ? ' active' : ''}" type="button" data-wish="1" aria-pressed="${wishFilterActive}">♥ wishlist (${wishlist.size})</button>`;
        filterList.innerHTML = cats + chip;
    }

    const EAGER_COUNT = 4;

    // Sizes hint mirrors the CSS grid breakpoints in style.css
    // (1 col ≤419, 2 cols ≤1024, 4 cols >1024; large cards span 2 cols).
    const SIZES_LARGE = '(max-width: 419px) 100vw, (max-width: 1024px) 100vw, 50vw';
    const SIZES_SMALL = '(max-width: 419px) 100vw, (max-width: 1024px) 50vw, 25vw';

    function buildPicture(item, query, index) {
        const raw = item.image?.trim();
        if (!raw) return '';
        const src     = escape(raw);
        const base    = src.replace(/\.png$/i, '');
        const isLarge = item.size === 'large';
        const sizes   = isLarge ? SIZES_LARGE : SIZES_SMALL;
        const srcset  = isLarge
            ? `${base}-800.webp 800w, ${base}-1600.webp 1600w`
            : `${base}-800.webp 800w`;

        let loadAttrs = 'decoding="async"';
        if (index >= EAGER_COUNT) loadAttrs += ' loading="lazy"';
        if (index === 0)          loadAttrs += ' fetchpriority="high"';

        const alt = escape(item.image_alt || query);
        return `
            <picture>
                <source type="image/webp" srcset="${srcset}" sizes="${sizes}">
                <img src="${src}" alt="${alt}" ${loadAttrs}>
            </picture>`;
    }

    function renderCard(item, index) {
        const brand = item.brand || '';
        const name  = item.name;
        const size  = item.size === 'large' ? 'large' : 'small';
        const query = brand ? `${brand} ${name}` : name;
        const url   = item.link || `https://www.google.com/search?q=${encodeURIComponent(query)}`;
        const fallback = brand || name;
        const queryEsc = escape(query);

        const flags = [
            item.framed && 'data-framed="true"',
            item.bleed  && 'data-bleed="true"',
        ].filter(Boolean).join(' ');

        const imgTag = buildPicture(item, query, index);
        const isSaved = wishlist.has(item.id);

        return `
            <div class="card ${size}" data-name="${queryEsc}"
                 data-category="${escape(item.category || '')}" ${flags}>
                <a class="card-link" href="${url}" target="_blank" rel="noopener noreferrer">
                    <div class="card-image">
                        <span class="card-image-fallback">${escape(fallback)}</span>
                        ${imgTag}
                    </div>
                </a>
                <div class="card-meta">
                    <a class="card-link card-text-link" href="${url}" target="_blank" rel="noopener noreferrer">
                        <span class="card-name">${escape(name)}</span>
                        ${brand ? `<span class="card-brand">${escape(brand)}</span>` : ''}
                    </a>
                    <button type="button" class="card-wish${isSaved ? ' saved' : ''}" data-wish-id="${escape(item.id)}"
                            aria-pressed="${isSaved}"
                            aria-label="${isSaved ? 'Remove from' : 'Add to'} wishlist: ${queryEsc}">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"
                             stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                            <path d="M12 20.6S4.5 16.2 2.1 11.5C.6 8.4 2.5 4.7 6 4.7c2.4 0 4.2 1.4 5 3 .8-1.6 2.6-3 5-3 3.5 0 5.4 3.7 3.9 6.8C17.5 16.2 12 20.6 12 20.6z"/>
                        </svg>
                    </button>
                </div>
            </div>
        `;
    }

    function markLoaded(img) {
        img.closest('.card-image')?.classList.add('has-image');
    }

    // Capture phase — `load` doesn't bubble.
    grid.addEventListener('load', e => {
        if (e.target.tagName === 'IMG') markLoaded(e.target);
    }, true);

    function markCachedImages() {
        for (const img of grid.querySelectorAll('img')) {
            if (img.complete && img.naturalWidth > 0) markLoaded(img);
        }
    }

    function visibleItems() {
        if (sharedIds) {
            const byId = new Map(items.map(i => [i.id, i]));
            return sharedIds.map(id => byId.get(id)).filter(Boolean);
        }
        let list = activeCategory === 'all'
            ? items
            : items.filter(i => i.category === activeCategory);
        if (wishFilterActive) list = list.filter(i => wishlist.has(i.id));
        return list;
    }

    function renderGrid(animate) {
        const visible = visibleItems();
        countEl.textContent = sharedIds
            ? `${visible.length} ${visible.length === 1 ? 'item' : 'items'} · shared list`
            : `${visible.length} ${visible.length === 1 ? 'item' : 'items'}`;
        grid.innerHTML = visible.map((item, i) => renderCard(item, i)).join('');
        markCachedImages();
        // Subtle stagger-in when switching filters (not on initial load).
        if (animate) {
            grid.classList.remove('grid-switching');
            void grid.offsetWidth; // restart the animation
            grid.classList.add('grid-switching');
            clearTimeout(grid._animTimer);
            grid._animTimer = setTimeout(
                () => grid.classList.remove('grid-switching'), 900
            );
        }
    }

    // Filter switch: fade the current cards out, jump to the top, then
    // render the new set with the stagger-in (skipped for reduced motion).
    function switchGrid() {
        const finish = () => {
            grid.classList.remove('grid-fading');
            void grid.offsetWidth;
            renderGrid(true);
        };
        if (reduceMotion || !grid.querySelector('.card')) {
            finish();
            return;
        }
        grid.classList.add('grid-fading');
        clearTimeout(grid._exitTimer);
        grid._exitTimer = setTimeout(finish, 190);
    }

    filterList.addEventListener('click', e => {
        const wishBtn = e.target.closest('.wish-filter');
        if (wishBtn) {
            sharedIds = null;
            // Wishlist is exclusive — selecting it drops any active category.
            activeCategory = 'all';
            wishFilterActive = !wishFilterActive;
            // Persist the wishlist view in the URL so refresh keeps it.
            const newUrl = wishFilterActive
                ? location.pathname + location.search + '#wishlist'
                : location.pathname + location.search;
            history.replaceState(null, '', newUrl);
            renderFilters();
            window.scrollTo({ top: 0, behavior: reduceMotion ? 'auto' : 'smooth' });
            switchGrid();
            return;
        }
        const btn = e.target.closest('.filter-link');
        if (!btn) return;
        sharedIds = null;
        const next = btn.dataset.cat;
        if (next === activeCategory && !wishFilterActive) return;
        // Category tabs are exclusive — selecting one clears the wishlist filter.
        wishFilterActive = false;
        activeCategory = next;
        const newUrl = next === 'all'
            ? location.pathname + location.search
            : '#' + next;
        history.replaceState(null, '', newUrl);
        renderFilters();
        window.scrollTo({ top: 0, behavior: reduceMotion ? 'auto' : 'smooth' });
        switchGrid();
    });

    // Heart-tap animation: burst particles, then the product image shrinks
    // and flies into the wishlist chip (skipped for reduced-motion users).
    const burstParticles = (x, y) => {
        const n = 8;
        for (let i = 0; i < n; i++) {
            const p = document.createElement('span');
            p.className = 'particle' + (i % 2 ? ' particle-grey' : '');
            p.style.left = (x - 2.5) + 'px';
            p.style.top  = (y - 2.5) + 'px';
            const ang = (Math.PI * 2 * i) / n + Math.random() * 0.6;
            const dist = 22 + Math.random() * 26;
            const tx = Math.cos(ang) * dist;
            const ty = Math.sin(ang) * dist;
            document.body.appendChild(p);
            requestAnimationFrame(() => requestAnimationFrame(() => {
                p.style.transform = `translate(${tx}px, ${ty}px) scale(0.4)`;
                p.style.opacity = '0';
            }));
            setTimeout(() => p.remove(), 560);
        }
    };
    const flyImage = (card, toRect) => {
        const img = card.querySelector('.card-image img');
        if (!img || !img.src) return;
        const fromRect = img.getBoundingClientRect();
        const dx = toRect.left + toRect.width / 2 - (fromRect.left + fromRect.width / 2);
        const dy = toRect.top + toRect.height / 2 - (fromRect.top + fromRect.height / 2);
        // Two nested layers, each animating one axis with a different easing
        // (horizontal: fast start; vertical: slow start) — together they trace
        // a curved swoop into the chip instead of a straight line.
        const wrap = document.createElement('span');
        wrap.className = 'img-fly';
        wrap.style.left = fromRect.left + 'px';
        wrap.style.top  = fromRect.top + 'px';
        wrap.style.width  = fromRect.width + 'px';
        wrap.style.height = fromRect.height + 'px';
        const fly = document.createElement('img');
        fly.className = 'img-fly-img';
        fly.src = img.src;
        fly.alt = '';
        wrap.appendChild(fly);
        document.body.appendChild(wrap);
        // The chip is a small pill, so the image ends up as a thumbnail.
        const endScale = Math.max(0.08, 34 / fromRect.width);
        requestAnimationFrame(() => requestAnimationFrame(() => {
            wrap.style.transform = `translateX(${dx}px)`;
            fly.style.transform  = `translateY(${dy}px) scale(${endScale})`;
            fly.style.opacity = '0.9';
        }));
        setTimeout(() => wrap.remove(), 700);
    };
    const bumpWishChip = () => {
        const chip = document.querySelector('.wish-filter');
        if (chip) {
            chip.classList.remove('bump');
            void chip.offsetWidth; // restart the animation
            chip.classList.add('bump');
        }
    };

    grid.addEventListener('click', e => {
        const heartBtn = e.target.closest('.card-wish');
        if (heartBtn) {
            const id = heartBtn.dataset.wishId;
            if (!id) return;
            const rect = heartBtn.getBoundingClientRect();
            const cx = rect.left + rect.width / 2;
            const cy = rect.top + rect.height / 2;
            const wasSaved = wishlist.has(id);
            if (wasSaved) wishlist.delete(id); else wishlist.add(id);
            persistWishlist();
            const saved = wishlist.has(id);
            heartBtn.classList.toggle('saved', saved);
            heartBtn.setAttribute('aria-pressed', String(saved));
            heartBtn.setAttribute('aria-label',
                `${saved ? 'Remove from' : 'Add to'} wishlist: ${heartBtn.closest('.card')?.dataset.name || ''}`);
            renderFilters();
            updateWishCta();
            if (wishFilterActive) renderGrid();
            // animation
            heartBtn.classList.add('tapped');
            setTimeout(() => heartBtn.classList.remove('tapped'), 400);
            if (saved && !reduceMotion) {
                burstParticles(cx, cy);
                const chip = document.querySelector('.wish-filter');
                if (chip) {
                    flyImage(heartBtn.closest('.card'), chip.getBoundingClientRect());
                    bumpWishChip();
                }
            }
            return;
        }
        const link = e.target.closest('.card-link');
        if (link && window.plausible) {
            const card = link.closest('.card');
            if (card) plausible('Item Click', { props: { name: card.dataset.name } });
        }
    });

    window.addEventListener('hashchange', () => {
        applyHash();
        renderFilters();
        renderGrid();
    });

    // Set SUBMIT_ENDPOINT to a Formspree/Netlify/Basin URL to POST directly;
    // otherwise submissions open the user's mail client to SUBMIT_TO.
    const SUBMIT_TO       = 'submissions@johnyvino.com';
    const SUBMIT_ENDPOINT = '';

    const submitButton = document.getElementById('submitButton');
    const submitModal  = document.getElementById('submitModal');
    const submitForm   = document.getElementById('submitForm');

    if (submitButton && submitModal && submitForm) {
        const openModal = () => {
            submitModal.classList.add('open');
            submitModal.setAttribute('aria-hidden', 'false');
            document.body.style.overflow = 'hidden';
            setTimeout(() => submitForm.querySelector('input')?.focus(), 80);
        };
        const closeModal = () => {
            submitModal.classList.remove('open');
            submitModal.setAttribute('aria-hidden', 'true');
            document.body.style.overflow = '';
        };

        submitButton.addEventListener('click', openModal);
        submitModal.addEventListener('click', e => {
            if (e.target.dataset.close !== undefined) closeModal();
        });
        document.addEventListener('keydown', e => {
            if (e.key === 'Escape' && submitModal.classList.contains('open')) closeModal();
        });

        submitForm.addEventListener('submit', async e => {
            e.preventDefault();
            const data = new FormData(submitForm);
            const fields = Object.fromEntries(data.entries());

            if (SUBMIT_ENDPOINT) {
                try {
                    const res = await fetch(SUBMIT_ENDPOINT, {
                        method: 'POST',
                        headers: { 'Accept': 'application/json' },
                        body: data,
                    });
                    if (res.ok) {
                        submitForm.reset();
                        closeModal();
                        alert('Thanks for the submission.');
                    } else {
                        alert('Submission failed. Please try again later.');
                    }
                } catch {
                    alert('Network error. Please try again.');
                }
                return;
            }

            const subject = `Submission: ${fields.name || ''} by ${fields.brand || ''}`;
            const body = [
                `Name:     ${fields.name || ''}`,
                `Brand:    ${fields.brand || ''}`,
                `Link:     ${fields.link || ''}`,
                `Category: ${fields.category || '—'}`,
                '',
                `Why is it well designed:`,
                fields.why || '—',
                '',
                `From: ${fields.from || 'anonymous'}`,
            ].join('\n');
            window.location.href =
                `mailto:${SUBMIT_TO}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
            submitForm.reset();
            closeModal();
        });
    }

    // Share wishlist: triggers in the filter bar + footer → popover with minimal social icons
    const footerActions = document.querySelector('.footer-actions');
    if (footerActions) {
        // Header trigger — share at the top of the page
        const header = document.querySelector('.site-header');
        if (header) {
            const headerShare = document.createElement('button');
            headerShare.type = 'button';
            headerShare.className = 'header-share';
            headerShare.textContent = 'share';
            headerShare.setAttribute('aria-label', 'Share your wishlist');
            headerShare.setAttribute('aria-expanded', 'false');
            headerShare.setAttribute('data-share-trigger', '1');
            header.appendChild(headerShare);
            headerShare.addEventListener('click', () => {
                if (pop.hidden) openPop(headerShare); else closePop();
            });
        }
        const shareBtn = document.createElement('button');
        shareBtn.type = 'button';
        shareBtn.className = 'footer-link';
        shareBtn.textContent = 'Share wishlist';
        shareBtn.setAttribute('aria-label', 'Share your wishlist');
        shareBtn.setAttribute('aria-expanded', 'false');
        shareBtn.setAttribute('data-share-trigger', '1');
        footerActions.appendChild(shareBtn);

        const pop = document.createElement('div');
        pop.className = 'share-pop';
        pop.hidden = true;
        pop.setAttribute('role', 'dialog');
        pop.setAttribute('aria-label', 'Share this list');
        document.body.appendChild(pop);

        let activeTrigger = null;

        const flash = (msg) => {
            shareBtn.textContent = msg;
            setTimeout(() => { shareBtn.textContent = 'Share wishlist'; }, 1800);
        };

        const wishlistUrl = () =>
            wishlist.size
                ? location.origin + location.pathname + '#w=' + [...wishlist].join(',')
                : location.href.split('#')[0];
        const shareText = () =>
            wishlist.size
                ? `My well-made picks — ${wishlist.size} ${wishlist.size === 1 ? 'object' : 'objects'} from Well Made`
                : 'Well Made — a handpicked collection of beautifully designed objects';

        const setExpanded = (btn, val) => { if (btn) btn.setAttribute('aria-expanded', String(val)); };
        const closePop = () => {
            pop.hidden = true;
            setExpanded(activeTrigger, false);
            activeTrigger = null;
        };

        const ICON_PATHS = {
            x: '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231 5.451-6.231zm-1.161 17.52h1.833L7.084 4.126H5.117l11.966 15.644z"/></svg>',
            facebook: '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M24 12.073C24 5.446 18.627.073 12 .073S0 5.446 0 12.073c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/></svg>',
            whatsapp: '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347zm-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884zm8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>',
            telegram: '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M11.944 0A12 12 0 000 12a12 12 0 0012 12 12 12 0 0012-12A12 12 0 0012 0a12 12 0 00-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 01.171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/></svg>',
            email: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" aria-hidden="true"><rect x="2.5" y="5" width="19" height="14" rx="2"/><path d="m3.5 7 8.5 6 8.5-6"/></svg>',
            more: '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><circle cx="12" cy="5.5" r="1.8"/><circle cx="12" cy="12" r="1.8"/><circle cx="12" cy="18.5" r="1.8"/></svg>',
        };

        const renderPop = () => {
            const url = wishlistUrl();
            const text = shareText();
            const enc = encodeURIComponent;
            const targets = [
                { key: 'x',        href: `https://twitter.com/intent/tweet?text=${enc(text)}&url=${enc(url)}`, label: 'Share on X' },
                { key: 'facebook', href: `https://www.facebook.com/sharer/sharer.php?u=${enc(url)}`, label: 'Share on Facebook' },
                { key: 'whatsapp', href: `https://api.whatsapp.com/send?text=${enc(text + ' ' + url)}`, label: 'Share on WhatsApp' },
                { key: 'telegram', href: `https://t.me/share/url?url=${enc(url)}&text=${enc(text)}`, label: 'Share on Telegram' },
                { key: 'email',    href: `mailto:?subject=${enc('My Well Made wishlist')}&body=${enc(text + '\n' + url)}`, label: 'Share by email' },
            ];
            let icons = targets.map(t =>
                `<a class="share-icon" href="${t.href}" target="_blank" rel="noopener noreferrer" aria-label="${t.label}" title="${t.label}">${ICON_PATHS[t.key]}</a>`
            ).join('');
            if (navigator.share) {
                icons += `<button type="button" class="share-icon" data-native="1" aria-label="More share options" title="More share options">${ICON_PATHS.more}</button>`;
            }
            const note = wishlist.size
                ? ''
                : '<div class="share-pop-note">Heart some picks with ♥ to build your list — or share the site itself.</div>';
            pop.innerHTML = `
                <div class="share-pop-head">
                    <span class="share-pop-title">${wishlist.size ? 'Share this list' : 'Share Well Made'}</span>
                    <button type="button" class="share-pop-close" aria-label="Close">×</button>
                </div>
                ${note}
                <div class="share-pop-icons">${icons}</div>
                <div class="share-pop-copy">
                    <input class="share-pop-input" type="text" readonly value="${url}" aria-label="Share link">
                    <button type="button" class="share-pop-copybtn" data-copy="1">Copy</button>
                </div>`;
            pop.querySelector('.share-pop-close').addEventListener('click', closePop);
            pop.querySelector('[data-copy]').addEventListener('click', e => {
                const btn = e.currentTarget;
                copyToClipboard(url, () => {
                    btn.textContent = 'Copied';
                    setTimeout(() => { btn.textContent = 'Copy'; }, 1600);
                });
            });
            const nativeBtn = pop.querySelector('[data-native]');
            if (nativeBtn) nativeBtn.addEventListener('click', () => {
                navigator.share({ title: 'Well Made wishlist', text, url }).catch(() => {});
            });
        };

        const openPop = (triggerBtn) => {
            renderPop();
            setExpanded(activeTrigger, false);
            activeTrigger = triggerBtn;
            setExpanded(activeTrigger, true);
            pop.hidden = false;
        };
        openSharePop = openPop;

        shareBtn.addEventListener('click', () => {
            if (pop.hidden) openPop(shareBtn); else closePop();
        });
        document.addEventListener('click', e => {
            if (!pop.hidden && !pop.contains(e.target) && !e.target.closest('[data-share-trigger]')) closePop();
        });
        document.addEventListener('keydown', e => {
            if (e.key === 'Escape' && !pop.hidden) closePop();
        });
    }

    // Wishlist call-to-action strip below the filter bar
    const gridEl = document.getElementById('grid');
    if (gridEl) {
        const ctaWrap = document.createElement('div');
        ctaWrap.className = 'wish-cta';
        const ctaText = document.createElement('span');
        ctaText.className = 'wish-cta-text';
        const ctaBtn = document.createElement('button');
        ctaBtn.type = 'button';
        ctaBtn.className = 'wish-cta-btn';
        ctaWrap.appendChild(ctaText);
        ctaWrap.appendChild(ctaBtn);
        gridEl.before(ctaWrap);

        updateWishCta = () => {
            if (wishlist.size) {
                ctaText.innerHTML = `You've saved <strong>${wishlist.size}</strong> ${wishlist.size === 1 ? 'pick' : 'picks'} — share your list with friends.`;
                ctaBtn.textContent = 'Share your list';
                ctaBtn.setAttribute('data-share-trigger', '1');
                ctaBtn.setAttribute('aria-expanded', 'false');
                ctaBtn.onclick = () => { if (openSharePop) openSharePop(ctaBtn); };
            } else {
                ctaText.innerHTML = 'Save your favorites with <strong>♥</strong> — then share your list with friends.';
                ctaBtn.textContent = 'Save a pick';
                ctaBtn.removeAttribute('data-share-trigger');
                ctaBtn.onclick = () => {
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                    const chip = document.querySelector('.wish-filter');
                    if (chip) {
                        chip.classList.add('pulse');
                        setTimeout(() => chip.classList.remove('pulse'), 2600);
                    }
                };
            }
        };
        updateWishCta();
    }

    // Hero header: shrink the big title into a slim bar on scroll (rAF-smoothed,
    // mirrors the minimalgoods.co effect via a --header-progress CSS var).
    const docRoot = document.documentElement;
    let heroCur = 0, heroTarget = 0, heroRaf = null;
    const heroProgress = () => {
        const t = window.scrollY / (window.innerHeight * 0.5);
        return t > 1 ? 1 : (t < 0 ? 0 : t);
    };
    const heroFrame = () => {
        heroCur += (heroTarget - heroCur) * (reduceMotion ? 1 : 0.15);
        if (Math.abs(heroTarget - heroCur) < 0.0005) heroCur = heroTarget;
        docRoot.style.setProperty('--header-progress', heroCur.toFixed(4));
        if (heroCur !== heroTarget) heroRaf = requestAnimationFrame(heroFrame);
        else heroRaf = null;
    };
    const heroSchedule = () => {
        heroTarget = heroProgress();
        if (!heroRaf) heroRaf = requestAnimationFrame(heroFrame);
    };
    window.addEventListener('scroll', heroSchedule, { passive: true });
    heroSchedule();

    renderFilters();
    renderGrid();

    // Page-load entrance: add .page-ready right after first paint so the
    // hero / filter bar / grid drift in once (skipped for reduced motion).
    if (!reduceMotion) {
        requestAnimationFrame(() => requestAnimationFrame(() =>
            document.body.classList.add('page-ready')));
    }
})();
