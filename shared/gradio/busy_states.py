# Copyright (c) 2026 DeepBeepMeep - part of WanGP, WanGP Community License 2.0 (see LICENSE.txt)
"""Client-side busy indicators (spinner, done tick, skeleton) wired onto marked Gradio events."""
import json
from functools import wraps

from gradio import blocks
from gradio.events import EventListenerMethod

_BUSY_EVENTS = {'click', 'upload'}

_JS_CORE = """
(() => {
    if (window.wangpBusy) return;
    const SPINNER_MS = 150, SKELETON_MS = 400, DONE_MS = 900, DEFAULT_TIMEOUT_MS = 60000;
    const active = new Map();
    let lastErrorAt = -1;
    const isError = (n) => n.nodeType === 1 && (n.matches?.('.toast-body.error') || n.querySelector?.('.toast-body.error'));
    const startObserver = () => {
        if (!document.body) return document.addEventListener('DOMContentLoaded', startObserver, {once: true});
        new MutationObserver((records) => {
            for (const r of records) for (const n of r.addedNodes) if (isError(n)) lastErrorAt = performance.now();
        }).observe(document.body, {childList: true, subtree: true});
    };
    startObserver();
    const resolve = (target) => {
        try {
            if (target) return document.querySelector(target);
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
                try { s.skeletonEl = document.querySelector(opts.skeleton); } catch (e) {}
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

_CSS_CORE = """
.wangp-busy { pointer-events: none; position: relative; box-shadow: inset 3px 3px 6px rgba(0,0,0,.35), inset -2px -2px 5px rgba(255,255,255,.07) !important; }
.wangp-busy .wangp-studio-icon::before { display: none; }
.wangp-busy::before { content: ""; display: inline-block; width: 14px; height: 14px; margin-right: 8px; border-radius: 50%; border: 2.5px solid currentColor; border-right-color: transparent; animation: wangp-spin .7s linear infinite; flex: none; vertical-align: middle; }
.wangp-busy-done { color: #6fdcb0 !important; }
.wangp-busy-done .wangp-studio-icon::before { display: none; }
.wangp-busy-done::before { content: "\2713"; display: inline-block; margin-right: 8px; font-weight: 900; }
.wangp-skeleton { position: relative; overflow: hidden; pointer-events: none; filter: saturate(.6); }
.wangp-skeleton > * { opacity: .25; transition: opacity .2s; }
.wangp-skeleton::after { content: ""; position: absolute; inset: 0; transform: translateX(-100%); background: linear-gradient(90deg, transparent, rgba(155,140,255,.10) 40%, rgba(255,255,255,.07) 50%, transparent 70%); animation: wangp-shimmer 1.3s ease-in-out infinite; pointer-events: none; }
@keyframes wangp-spin { to { transform: rotate(360deg); } }
@keyframes wangp-shimmer { to { transform: translateX(100%); } }
@media (prefers-reduced-motion: reduce) {
    .wangp-busy::before { animation: none; border-right-color: currentColor; opacity: .6; }
    .wangp-skeleton::after { animation: none; transform: none; }
}
"""


def get_javascript():
    return _JS_CORE


def get_css():
    return _CSS_CORE


def start_js(key, target):
    return '(...a) => { window.wangpBusy?.start(%s, %s); return a; }' % (json.dumps(key), json.dumps(target))


def end_js(key):
    return '() => { window.wangpBusy?.end(%s); }' % json.dumps(key)


def mark_busy(component, key, target=None):
    if target is None and getattr(component, 'elem_id', None):
        target = f'#{component.elem_id}'
    component._wangp_busy = (key, target)
    return component


def _wire(app):
    wired = app.__dict__.setdefault('_wangp_busy_wired', set())
    for fn in list(app.fns.values()):
        if fn._id in wired:
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
        app.default_config.set_event_trigger([EventListenerMethod(None, 'then')], None, None, None, js=end_js(key), trigger_after=fn._id, trigger_only_on_success=False, queue=False, api_name=False)


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
