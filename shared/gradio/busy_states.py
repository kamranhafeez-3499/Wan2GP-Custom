# Copyright (c) 2026 DeepBeepMeep - part of WanGP, WanGP Community License 2.0 (see LICENSE.txt)
"""Client-side busy indicators (spinner, done tick, skeleton) wired onto marked Gradio events."""
import json
from functools import wraps

from gradio import blocks
from gradio.events import EventListenerMethod
from shared.model_capabilities import capabilities_payload  # re-exported for wgp.py

_BUSY_EVENTS = {'click', 'upload'}

_JS_CORE = """
(() => {
    if (window.wangpBusy) return;
    const SPINNER_MS = 150, SKELETON_MS = 400, DONE_MS = 900, DEFAULT_TIMEOUT_MS = 60000;
    const active = new Map();
    let lastErrorAt = -1;
    const isError = (n) => n.nodeType === 1 && (n.matches?.('.toast-body.error') || n.querySelector?.('.toast-body.error'));
    // Observe only Gradio's toast container (a persistent child of <main>): a document-wide subtree
    // observer ran querySelector on every node added during the form rebuild.
    let toastWrap = null, toastObserver = null;
    const attachToasts = () => {
        const wrap = document.querySelector('.toast-wrap');
        if (wrap === toastWrap) return;
        toastObserver?.disconnect();
        toastWrap = wrap;
        if (!wrap) return;
        toastObserver = new MutationObserver((records) => {
            for (const r of records) for (const n of r.addedNodes) if (isError(n)) { lastErrorAt = performance.now(); for (const k of [...active.keys()]) end(k, {ok: false}); }
        });
        toastObserver.observe(wrap, {childList: true, subtree: true});
    };
    attachToasts();
    setInterval(attachToasts, 1000);
    // Safari / macOS Firefox do not focus a button on click, so remember the last pressed button ourselves.
    let lastPressed = null, lastPressedAt = 0;
    document.addEventListener('pointerdown', (e) => {
        lastPressed = e.target?.closest?.('button') || null;
        lastPressedAt = performance.now();
    }, true);
    const resolve = (target) => {
        try {
            if (target) return document.querySelector(target);
            if (lastPressed?.isConnected && performance.now() - lastPressedAt < 1000) return lastPressed;
            return document.activeElement?.closest?.('button') || null;
        } catch (e) { return null; }
    };
    const clearTimers = (s) => s.timers.forEach(clearTimeout);
    function end(key, opts) {
        const s = active.get(key);
        if (!s) return;
        active.delete(key);
        clearTimers(s);
        const el = s.el;
        el?.classList.remove('wangp-busy');
        s.skeletonEl?.classList.remove('wangp-skeleton');
        const ok = !opts || opts.ok !== false;
        if (el && ok && s.spinnerShown && !(lastErrorAt >= s.startedAt)) {
            el.classList.add('wangp-busy-done');
            setTimeout(() => el.classList.remove('wangp-busy-done'), DONE_MS);
        }
    }
    function start(key, target, opts) {
        if (active.has(key)) return;
        opts = opts || {};
        const s = {el: resolve(target), skeletonEl: null, startedAt: performance.now(), spinnerShown: false, timers: []};
        active.set(key, s);
        s.timers.push(setTimeout(() => {
            s.spinnerShown = true;
            s.el?.classList.remove('wangp-busy-done');
            s.el?.classList.add('wangp-busy');
        }, SPINNER_MS));
        if (opts.skeleton) {
            s.timers.push(setTimeout(() => {
                try { s.skeletonEl = typeof opts.skeleton === 'function' ? opts.skeleton() : document.querySelector(opts.skeleton); } catch (e) {}
                s.skeletonEl?.classList.add('wangp-skeleton');
            }, SKELETON_MS));
        }
        s.timers.push(setTimeout(() => {
            console.warn('wangpBusy: safety timeout for', key);
            end(key, {ok: false});
        }, opts.timeoutMs ?? DEFAULT_TIMEOUT_MS));
    }
    window.wangpBusy = {start, end};
})();
"""

_JS_MODEL_SWITCH = r"""
(() => {
    if (window.wangpModelSwitchWired) return;
    window.wangpModelSwitchWired = true;
    const PICK = '#family_list li.item, #model_base_types_list li.item, #model_list li.item';
    let lastPicked = '', pickedAt = 0;
    document.addEventListener('mousedown', (e) => {
        const li = e.target?.closest?.(PICK);
        if (li) { lastPicked = cleanName(li.textContent); pickedAt = performance.now(); }
    }, true);
    // Enqueue follows the pick within one round trip, so a pick older than 2 s is stale.
    const freshPick = () => (lastPicked && performance.now() - pickedAt < 2000) ? lastPicked : '';
    const fallbackName = () => cleanName(document.querySelector('#model_list input')?.value);
    // Status squares from MODEL_STATUS_PREFIXES plus the tick Gradio prepends to the selected dropdown item.
    const STATUS_PREFIX = /^[\u2713\u2B1B\u{1F7E6}\u{1F7E8}\s]+/u;
    const cleanName = (t) => (t || '').replace(STATUS_PREFIX, '').trim();
    // The settings column carries .wangp-actions-column only with the floating generate button; otherwise
    // use the first row after the model selector that holds a visible textarea (the prompt).
    const settingsColumn = () => {
        const fixed = document.querySelector('.wangp-actions-column');
        if (fixed) return fixed;
        let row = document.querySelector('#family_list')?.closest?.('.row')?.nextElementSibling;
        for (; row; row = row.nextElementSibling) if ([...row.querySelectorAll('textarea')].some(t => t.offsetParent)) return row.querySelector('.column') || row;
        return null;
    };
    const lineEl = () => {
        let el = document.getElementById('wangp_switching_line');
        if (el) return el;
        const row = document.querySelector('#family_list')?.closest('.row');
        if (!row) return null;
        el = document.createElement('div');
        el.id = 'wangp_switching_line';
        el.style.display = 'none';
        row.insertAdjacentElement('afterend', el);
        return el;
    };
    window.addEventListener('wangp:model-switch-start', () => {
        window.wangpBusy?.start('model', '#model_list', {skeleton: settingsColumn, timeoutMs: 120000});
        const el = lineEl();
        if (!el) return;
        const name = freshPick();
        // Only a fresh pick may overwrite a line already shown in this busy period.
        if (name || !el.classList.contains('wangp-on')) el.textContent = 'Switching to ' + (name || fallbackName()) + '… rebuilding settings';
        el.classList.add('wangp-on');
    });
    window.addEventListener('wangp:model-switch-end', () => {
        window.wangpBusy?.end('model');
        const el = document.getElementById('wangp_switching_line');
        if (el) el.classList.remove('wangp-on');
        lastPicked = '';
    });
})();
"""

_CSS_CORE = r"""
.wangp-busy { pointer-events: none; position: relative; box-shadow: inset 3px 3px 6px rgba(0,0,0,.35), inset -2px -2px 5px rgba(255,255,255,.07) !important; }
.wangp-busy .wangp-studio-icon::before { display: none; }
.wangp-busy::before { content: ""; display: inline-block; width: 14px; height: 14px; margin-right: 8px; border-radius: 50%; border: 2.5px solid currentColor; border-right-color: transparent; animation: wangp-spin .7s linear infinite; flex: none; vertical-align: middle; }
.wangp-busy-done { color: #6fdcb0 !important; }
.wangp-busy-done .wangp-studio-icon::before { display: none; }
.wangp-busy-done::before { content: "\2713"; display: inline-block; margin-right: 8px; font-weight: 900; }
#model_list.wangp-busy::before, #model_list.wangp-busy-done::before { position: absolute; top: 50%; right: 14px; z-index: 3; margin: -7px 0 0 0; line-height: 14px; }
#model_list.wangp-busy .icon-wrap, #model_list.wangp-busy-done .icon-wrap { opacity: 0; }
.wangp-skeleton { position: relative; overflow: hidden; pointer-events: none; filter: saturate(.6); }
.wangp-skeleton > * { opacity: .25; transition: opacity .2s; }
.wangp-skeleton::after { content: ""; position: absolute; inset: 0; transform: translateX(-100%); background: linear-gradient(90deg, transparent, rgba(155,140,255,.10) 40%, rgba(255,255,255,.07) 50%, transparent 70%); animation: wangp-shimmer 1.3s ease-in-out infinite; pointer-events: none; }
@keyframes wangp-spin { to { transform: rotate(360deg); } }
@keyframes wangp-shimmer { to { transform: translateX(100%); } }
#wangp_switching_line { color: #c4baff; font-size: 13px; font-weight: bold; padding: 4px 2px; }
#wangp_switching_line.wangp-on { display: block !important; }
@media (prefers-reduced-motion: reduce) {
    .wangp-busy::before { animation: none; border-right-color: currentColor; opacity: .6; }
    .wangp-skeleton::after { animation: none; transform: none; }
}
"""


_JS_DIMMING = r"""
(() => {
    if (window.wangpDimmingWired) return;
    window.wangpDimmingWired = true;
    const TOP = {'Mask Generator': c => c.mask, 'Motion Designer': c => c.motion};
    const GALLERY = {'Video / Images': c => c.video || c.image, 'Audio Files': c => c.audio, '3D': c => c.mesh};
    let state = null;
    const setNa = (btn, na, name) => {
        btn.classList.toggle('wangp-na', na);
        if (na) btn.setAttribute('data-wangp-tip', 'Not used by ' + name);
        else btn.removeAttribute('data-wangp-tip');
    };
    const applyTabs = () => {
        if (!state) return;
        const c = state.caps || {}, name = state.model_name || 'this model';
        // Gradio renders each tab bar twice (a visually-hidden measuring copy), so classify per bar.
        for (const bar of document.querySelectorAll('.tab-container, .tab-wrapper')) {
            const bs = Array.from(bar.querySelectorAll('button'));
            const inGallery = bs.some(b => (b.textContent || '').trim() === 'Video / Images');
            for (const b of bs) {
                const label = (b.textContent || '').trim();
                const rule = (inGallery ? GALLERY : TOP)[label];
                if (rule) setNa(b, !rule(c), name);
            }
        }
    };
    const applyUnload = () => {
        const btn = document.getElementById('wangp_model_tool_unload');
        if (!btn) return;
        const status = Array.from(document.querySelectorAll('.wangp-progress')).find(e => (e.textContent || '').includes('No Model is Loaded'));
        const na = !!status;
        btn.classList.toggle('wangp-na', na);
        if (na) { btn.setAttribute('aria-disabled', 'true'); btn.setAttribute('data-wangp-tip', 'Nothing is loaded in RAM'); }
        else { btn.removeAttribute('aria-disabled'); btn.removeAttribute('data-wangp-tip'); }
    };
    let lastRaw = null;
    const readCaps = () => {
        const ta = document.querySelector('#wangp_model_caps textarea, #wangp_model_caps input');
        if (!ta || !ta.value || ta.value === lastRaw) return;
        try { state = JSON.parse(ta.value); lastRaw = ta.value; } catch (e) { return; }
    };
    // Polling instead of a document-wide MutationObserver: Gradio's form rebuild fires thousands of
    // mutations and observer callbacks sat on the critical path. The textarea value changes without
    // DOM mutations anyway, and classList/attribute writes below are no-ops when nothing changed.
    let switching = false;
    const refresh = () => { if (document.hidden || switching) return; readCaps(); applyTabs(); applyUnload(); };
    document.addEventListener('input', (e) => { if (e.target?.closest?.('#wangp_model_caps')) refresh(); }, true);
    window.addEventListener('wangp:model-switch-start', () => { switching = true; setTimeout(() => { switching = false; }, 20000); });
    window.addEventListener('wangp:model-switch-end', () => { switching = false; setTimeout(refresh, 150); setTimeout(refresh, 600); });
    setInterval(refresh, 400);
    refresh();
})();
"""

_CSS_DIMMING = r"""
.wangp-na { opacity: .38; cursor: help; position: relative; }
[data-wangp-tip] { position: relative; }
.tab-container:has(> .wangp-na) { overflow: visible; }
[data-wangp-tip]:hover::after { content: attr(data-wangp-tip); position: absolute; bottom: calc(100% + 10px); left: 50%; transform: translateX(-50%); white-space: nowrap; z-index: 1000; padding: 7px 11px; border-radius: 10px; font-size: 12px; font-weight: 700; color: #eceaf6; background: #3a3b50; box-shadow: 6px 6px 14px rgba(0,0,0,.45), -3px -3px 8px rgba(255,255,255,.05); opacity: 1; pointer-events: none; }
"""

_JS_GALLERY = r"""
(() => {
    if (window.wangpGalleryWired) return;
    window.wangpGalleryWired = true;
    const CLS = 'wangp-media-loading';
    const SEL = 'button.thumbnail-item, .thumbnail-small';
    const pending = (m) => m.tagName === 'VIDEO' ? m.readyState < 1 : !m.complete;  // metadata is enough for a poster frame
    const watch = (thumb) => {
        const media = thumb.querySelector('img, video');
        if (!media) return;
        if (thumb._wangpMedia === media) return;
        thumb._wangpMedia = media;
        if (!pending(media)) { thumb.classList.remove(CLS); return; }
        thumb.classList.add(CLS);
        const done = () => { clearTimeout(timer); thumb.classList.remove(CLS); };
        const timer = setTimeout(done, 10000);  // never leave media hidden behind the shimmer
        for (const ev of ['load', 'loadedmetadata', 'loadeddata', 'error']) media.addEventListener(ev, done, {once: true});
    };
    // Poll instead of a document-wide subtree observer: new thumbnails are picked up within 500 ms and the
    // form rebuild of a model switch no longer triggers a scan per mutation burst.
    const scan = () => { if (!document.hidden) document.querySelectorAll(SEL).forEach(watch); };
    setInterval(scan, 500);
    scan();
})();
"""

_CSS_GALLERY = r"""
.wangp-media-loading { position: relative; overflow: hidden; background: #1c1d27; }
.wangp-media-loading > img, .wangp-media-loading > video { opacity: 0; }
.wangp-media-loading::after { content: ""; position: absolute; inset: 0; transform: translateX(-100%); background: linear-gradient(90deg, transparent, rgba(155,140,255,.10) 40%, rgba(255,255,255,.07) 50%, transparent 70%); animation: wangp-shimmer 1.3s ease-in-out infinite; pointer-events: none; }
@media (prefers-reduced-motion: reduce) {
    .wangp-media-loading::after { animation: none; transform: none; }
}
"""

_HEAD_STYLE = r"""
#wangp_page_skeleton { position: fixed; inset: 0; z-index: 9999; background: #22232f; transition: opacity .25s; display: grid; align-content: start; gap: 16px; padding: 18px; box-sizing: border-box; overflow: hidden; }
#wangp_page_skeleton .r { display: flex; gap: 12px; }
#wangp_page_skeleton .g { flex: 1; min-width: 0; display: grid; gap: 12px; align-content: start; }
#wangp_page_skeleton .sk { position: relative; overflow: hidden; background: #1c1d27; border-radius: 12px; box-shadow: inset 3px 3px 7px rgba(0,0,0,.35), inset -3px -3px 7px rgba(255,255,255,.07); }
#wangp_page_skeleton .sk::after { content: ""; position: absolute; inset: 0; transform: translateX(-100%); background: linear-gradient(90deg, transparent, rgba(155,140,255,.10) 40%, rgba(255,255,255,.07) 50%, transparent 70%); animation: wangp-pagesk-shimmer 1.3s ease-in-out infinite; }
#wangp_page_skeleton .sk.line { height: 12px; border-radius: 999px; }
@keyframes wangp-pagesk-shimmer { to { transform: translateX(100%); } }
@media (prefers-reduced-motion: reduce) {
    #wangp_page_skeleton .sk::after { animation: none; transform: none; }
}
"""

_HEAD_JS = r"""
(function () {
    var HTML = '<div id="wangp_page_skeleton" aria-hidden="true">'
        + '<div class="r"><div class="sk" style="width:120px;height:26px"></div><div style="flex:1"></div><div class="sk" style="width:380px;max-width:50%;height:34px;border-radius:999px"></div></div>'
        + '<div class="r"><div class="sk" style="width:190px;height:42px"></div><div class="sk" style="flex:1;height:42px"></div><div class="sk" style="flex:1;height:42px"></div></div>'
        + '<div class="r"><div class="g"><div class="sk" style="height:38px"></div><div class="sk" style="height:110px"></div><div class="sk line"></div><div class="sk line" style="width:70%"></div></div><div class="sk" style="flex:1;height:200px"></div></div>'
        + '</div>';
    var done = false;
    function remove(el) {
        if (done) return;
        done = true;
        clearInterval(timer);
        el.style.pointerEvents = 'none';
        el.style.opacity = '0';
        setTimeout(function () { el.remove(); }, 250);
    }
    var timer;
    function mount() {
        if (document.getElementById('wangp_page_skeleton')) return;
        var host = document.createElement('div');
        host.innerHTML = HTML;
        var el = host.firstChild;
        document.body.insertBefore(el, document.body.firstChild);
        var started = Date.now();
        timer = setInterval(function () {
            // #family_list exists only in the normal build; --lock-model renders the main tabs without it.
            var ready = document.querySelector('#family_list') || (document.querySelector('[role="tab"]') && Date.now() - started >= 1500);
            if (ready || Date.now() - started >= 20000) remove(el);
        }, 100);
        setTimeout(function () { remove(el); }, 20000);
    }
    // Mount as soon as <body> exists (module scripts delay DOMContentLoaded); DOMContentLoaded is the fallback.
    if (document.body) mount();
    else {
        var mo = new MutationObserver(function () { if (document.body) { mo.disconnect(); mount(); } });
        mo.observe(document.documentElement, {childList: true});
        document.addEventListener('DOMContentLoaded', function () { mo.disconnect(); mount(); });
    }
})();
"""


def get_head_html():
    return '<style>' + _HEAD_STYLE + '</style><script>' + _HEAD_JS + '</script>'


def get_javascript():
    return _JS_CORE + _JS_MODEL_SWITCH + _JS_DIMMING + _JS_GALLERY


def get_css():
    return _CSS_CORE + _CSS_DIMMING + _CSS_GALLERY


def start_js(key, target):
    return '(...a) => { window.wangpBusy?.start(%s, %s); return a; }' % (json.dumps(key), json.dumps(target))


def end_js(key):
    return '() => { window.wangpBusy?.end(%s); }' % json.dumps(key)


def mark_busy(component, key, target=None):
    if target is None and getattr(component, 'elem_id', None):
        target = f'#{component.elem_id}'
    component._wangp_busy = (key, target)
    return component


def _chain_tail(app, root, ends):
    # Tail of the longest .then/.success path below root (ties: most recently registered fn).
    children = {}
    for f in app.fns.values():
        if f.trigger_after is not None and f._id not in ends:
            children.setdefault(f.trigger_after, []).append(f)

    def longest(f, seen):
        best = (0, f._id, f)
        for c in children.get(f._id, []):
            if c._id in seen:
                continue
            d, _, t = longest(c, seen | {c._id})
            cand = (d + 1, t._id, t)
            if cand[:2] > best[:2]:
                best = cand
        return best

    return longest(root, {root._id})[2]


def _wire(app):
    wired = app.__dict__.setdefault('_wangp_busy_wired', set())
    ends = app.__dict__.setdefault('_wangp_busy_ends', set())
    for fn in list(app.fns.values()):
        if fn._id in wired or fn._id in ends:
            continue
        marked = None
        for block_id, event in fn.targets:
            block = app.blocks.get(block_id)
            if block is not None and event in _BUSY_EVENTS and getattr(block, '_wangp_busy', None):
                marked = block._wangp_busy
                break
        if marked is None:
            continue
        wired.add(fn._id)
        key, target = marked
        if fn.js is None:
            fn.js = start_js(key, target)
        else:
            fn.js = '(...a) => { window.wangpBusy?.start(%s, %s); return (%s)(...a); }' % (json.dumps(key), json.dumps(target), fn.js)
        tail = _chain_tail(app, fn, ends)
        app.default_config.set_event_trigger([EventListenerMethod(None, 'then')], None, None, None, js=end_js(key), trigger_after=tail._id, trigger_only_on_success=False, queue=False, api_name=False)
        ends.update(f._id for f in app.fns.values() if f._id not in wired and f._id not in ends and f.js == end_js(key) and f.trigger_after == tail._id)


def install():
    original = blocks.Blocks.get_config_file
    if getattr(original, '_wangp_busy_installed', False):
        return

    @wraps(original)
    def get_config_file(self):
        _wire(self)
        return original(self)

    get_config_file._wangp_busy_installed = True
    blocks.Blocks.get_config_file = get_config_file
