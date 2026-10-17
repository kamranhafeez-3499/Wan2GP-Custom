# Loading States & Model-Aware UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show Dark Clay loading states for every slow action and dim UI parts the selected model cannot use.

**Architecture:** A client-side busy layer (`window.wangpBusy`) is driven by (a) `js` start hooks + end-only `.then` continuations attached post-build to marked buttons, and (b) browser events dispatched from WanGP's existing model-switch queue JS. A pure `get_model_capabilities(model_def)` feeds one hidden JSON component updated on model switch; browser JS dims tabs from it. Everything visual lives in new modules plus `ui_studio_dark_clay.css`; `wgp.py` changes stay ≤ 10 lines.

**Tech Stack:** Python 3.11, Gradio 5.29.0 (pinned; frontend patches depend on it), vanilla JS/CSS, pytest, Playwright MCP for UI verification.

**Spec:** `docs/superpowers/specs/2026-10-17-loading-states-model-aware-design.md`

## Global Constraints

- Thresholds: nothing < 150 ms; spinner ≥ 150 ms; skeleton ≥ 400 ms (model switch only); ✓ shown 900 ms after a success that showed a spinner; safety timeout 60 000 ms (per-key override).
- Busy buttons keep their label; spinner replaces the icon; control is pressed and inert while busy.
- `prefers-reduced-motion: reduce` → no spin/shimmer animation (static indicators).
- Dimmed ("not available") items: opacity `0.38`, `cursor: help`, tooltip text exactly `Not used by <model name>`, still clickable.
- All JS hooks use optional chaining (`window.wangpBusy?.…`) so non-Dark-Clay themes behave exactly as today.
- Visual features (busy CSS, skeletons, dimming, page skeleton) are active only when `UI_theme == "dark_clay"`; the JS API exists in all themes but its CSS is only loaded with Dark Clay.
- `wgp.py`: ≤ 10 changed lines total across all tasks.
- Do not modify `plugins/motion_designer/plugin.py` or Gradio match strings (the keys of `_REPLACEMENTS`) in `gradio_model_change_queue.py`.
- Tests live in `tests/` (gitignored by the repo's `.gitignore:57`): run them, do not commit them. Run with `.venv\Scripts\python.exe -m pytest <path> -q -p no:cacheprovider`.
- Restart the UI for UI checks: stop the running `run_ui_cpu.py` process tree, then `.venv\Scripts\python.exe run_ui_cpu.py` (wait for `Running on local URL`).

**Spec deviation (recorded):** the spec puts the model-switch end hook in the ack continuation's `js`. The patched frontend intercepts that dependency (`if(pe.wangp_model_end){wangpModelRelease(S);return}`) before its `js` runs, so instead Task 3 dispatches `wangp:model-switch-start` / `wangp:model-switch-end` window events from `wangpModelEnqueue` / `wangpModelRelease` inside `_QUEUE_JS`. Same guarantees (release runs on success, error and connection failure).

**Spec deviation (recorded):** capability flags are not in `defaults/*.json`; architecture handlers add them at runtime. Capability tests therefore use dict fixtures shaped like the handler output (e.g. `models/wan/wan_handler.py:429-442`), and Task 8 checks real models in the running UI.

## Review Focus

1. A busy handler that raises server-side → spinner must still clear (end continuation runs after failure; Task 2 test asserts `trigger_only_on_success` is False on the end dependency).
2. Rapid double-click / two switches queued back to back → one spinner, cleared only when the queue is empty (Task 3 counts enqueue/release; Task 8 double-click check).
3. A model whose `mask_preprocessing.selection == [""]` with `visible: False` (e.g. `wan_handler.py:478`) → Mask Generator must be dimmed, not enabled (Task 1 test `test_mask_hidden_selection_is_not_capable`).
4. Model definition missing every flag or malformed (`None`, non-dict selection) → nothing dimmed (all caps True) and no exception (Task 1 test `test_malformed_defs_enable_everything`).
5. Theme other than Dark Clay → zero visual change and no console errors (Task 8 check with `UI_theme=default`).

---

### Task 1: Model capabilities function

**Files:**
- Create: `shared/model_capabilities.py`
- Test: `tests/test_model_capabilities.py`

**Interfaces:**
- Produces: `get_model_capabilities(model_def: dict | None) -> dict[str, bool]` with exactly the keys `mask, motion, video, image, audio, mesh`.
- Produces: `capabilities_payload(model_name: str, model_def: dict | None) -> str` — JSON string `{"model_name": <str>, "caps": <dict>}` (used by Task 5).

Rules (the implementer writes the bodies):
- `selection_used(entry)`: True when `entry` is a dict, `entry.get("visible", True)` is not False, and its `selection` list contains at least one non-empty string.
- `mask` = `selection_used(model_def.get("mask_preprocessing"))` or `selection_used(model_def.get("guide_preprocessing"))` or `selection_used(model_def.get("image_ref_choices"))`.
- `motion` = any of `i2v_v2v`, `vace_class`, `i2v_trajectory` truthy — comment: `# mirrors plugins/motion_designer/plugin.py:176-187 (on_tab_select)`.
- `image` = truthy `image_outputs`; `audio` = truthy `audio_only`; `mesh` = truthy `mesh_outputs`; `video` = not (`image` or `audio` or `mesh`).
- Malformed input (`None`, non-dict, any exception) → all six keys True; log once with `print("[model_capabilities] ...")` per model name (module-level set of warned names).

- [ ] **Step 1: Write the failing tests**

```python
from shared.model_capabilities import get_model_capabilities, capabilities_payload
import json

WAN_VACE = {"vace_class": True, "guide_preprocessing": {"selection": ["", "PV", "DV"]}, "mask_preprocessing": {"selection": ["", "A"]}}
WAN_T2V = {}
FLUX_IMG = {"image_outputs": True}
ACE_AUDIO = {"audio_only": True}
MESH = {"mesh_outputs": True}
HIDDEN_MASK = {"mask_preprocessing": {"selection": [""], "visible": False}}

def test_t2v_is_plain_video():
    assert get_model_capabilities(WAN_T2V) == {"mask": False, "motion": False, "video": True, "image": False, "audio": False, "mesh": False}

def test_vace_supports_mask_and_motion():
    caps = get_model_capabilities(WAN_VACE)
    assert caps["mask"] and caps["motion"] and caps["video"]

def test_output_kinds():
    assert get_model_capabilities(FLUX_IMG)["image"] and not get_model_capabilities(FLUX_IMG)["video"]
    assert get_model_capabilities(ACE_AUDIO)["audio"] and not get_model_capabilities(ACE_AUDIO)["video"]
    assert get_model_capabilities(MESH)["mesh"] and not get_model_capabilities(MESH)["video"]

def test_mask_hidden_selection_is_not_capable():
    assert get_model_capabilities(HIDDEN_MASK)["mask"] is False

def test_motion_flags_each_enable_motion():
    for key in ("i2v_v2v", "vace_class", "i2v_trajectory"):
        assert get_model_capabilities({key: True})["motion"] is True

def test_malformed_defs_enable_everything():
    for bad in (None, "x", {"mask_preprocessing": {"selection": None}}):
        caps = get_model_capabilities(bad)
        assert set(caps) == {"mask", "motion", "video", "image", "audio", "mesh"}
    assert all(get_model_capabilities(None).values())

def test_payload_shape():
    data = json.loads(capabilities_payload("Text2video 14B", WAN_T2V))
    assert data == {"model_name": "Text2video 14B", "caps": get_model_capabilities(WAN_T2V)}
```

Note: `{"mask_preprocessing": {"selection": None}}` is malformed only for that entry — `selection_used` must return False for it (not raise); the assertion only checks the key set.

- [ ] **Step 2: Run** `.venv\Scripts\python.exe -m pytest tests/test_model_capabilities.py -q -p no:cacheprovider` — Expected: FAIL (`ModuleNotFoundError: shared.model_capabilities`).
- [ ] **Step 3: Implement** `shared/model_capabilities.py` per the rules above (stdlib only: `json`).
- [ ] **Step 4: Run** the same command — Expected: `7 passed`.
- [ ] **Step 5: Commit** `git add shared/model_capabilities.py` → `git commit -m "feat: add model capability flags for model-aware UI"` (plus the Co-Authored-By trailer).

---

### Task 2: Busy layer core (`busy_states.py`)

**Files:**
- Create: `shared/gradio/busy_states.py`
- Test: `tests/test_busy_states.py`

**Interfaces:**
- Produces: `mark_busy(component, key: str, target: str | None = None) -> component` — tags a component (`component._wangp_busy = (key, target or f"#{component.elem_id}" or None)`); returns it for inline use. If `target` is None and the component has no `elem_id`, the JS resolves the target from the clicked element (the event's `document.activeElement` closest `button`).
- Produces: `install()` — idempotent; wraps `gradio.blocks.Blocks.get_config_file` (same pattern as `gradio_model_change_queue.install`, guard attribute `_wangp_busy_installed`) so that, before the original runs, for every `fn` in `self.fns.values()` whose `targets` include `(block_id, event)` with `event in {"click", "upload"}` for a marked block:
  - `fn.js` becomes `start_js(key, target)` if it was None, else a composition `"(...a) => { window.wangpBusy?.start(KEY, TARGET); return (EXISTING)(...a); }"`;
  - one end-only continuation is registered once per fn: `self.default_config.set_event_trigger([EventListenerMethod(None, "then")], None, None, None, js=end_js(key), trigger_after=fn._id, trigger_only_on_success=False, queue=False, api_name=False)`; remember wired fn ids on the app to stay idempotent.
- Produces: `start_js(key: str, target: str | None) -> str`, `end_js(key: str) -> str` (pure string builders; keys/targets JSON-encoded with `json.dumps`).
- Produces: `get_css() -> str`, `get_javascript() -> str`.
- JS API (`get_javascript`): `window.wangpBusy = { start(key, target, opts), end(key, opts) }` implementing the Global Constraints thresholds; classes `wangp-busy`, `wangp-busy-done`, `wangp-skeleton`; `opts = {skeleton?: selector, timeoutMs?: number, ok?: boolean}`; repeated `start` for an active key is a no-op; `end` for an unknown key is a no-op.
- Success vs failure: the end continuation cannot tell them apart (it runs either way), so `end` shows the ✓ only when `opts.ok !== false`, the spinner had appeared, **and** no Gradio error toast (`.toast-body.error`) was added to the DOM between `start` and `end` (one shared MutationObserver on `document.body` records the time of the last error toast; compare with the key's start time).
- CSS (`get_css`): `.wangp-busy` (pressed shadow, `pointer-events:none`, spinner via `::before`, hides `.wangp-studio-icon::before` mask icon), `.wangp-busy-done` (✓ in `#6fdcb0`), `.wangp-skeleton` (dim children to `opacity:.25`, overlay shimmer `::after`), reduced-motion overrides. Values from the mockup `.superpowers/brainstorm/1081-1792220591/content/loading-states.html` (`.btn.busy`, `.sk`, `.panel.loading`).

- [ ] **Step 1: Write the failing tests**

```python
import gradio as gr
from shared.gradio import busy_states

def build():
    busy_states.install()
    with gr.Blocks() as demo:
        a = busy_states.mark_busy(gr.Button("Apply", elem_id="t_apply"), "apply")
        b = gr.Button("Other", elem_id="t_other")
        out = gr.Textbox()
        a.click(lambda: "x", None, out)
        b.click(lambda: "y", None, out)
        a.click(lambda: "z", None, out, js="(v) => v")
    return demo, demo.get_config_file()

def test_start_js_added_and_existing_js_composed():
    demo, cfg = build()
    deps = cfg["dependencies"]
    js = [d["js"] for d in deps if d["js"]]
    assert any("wangpBusy?.start(\"apply\", \"#t_apply\")" in j for j in js)
    assert any("(v) => v" in j and "wangpBusy?.start" in j for j in js)

def test_end_continuation_runs_on_failure_and_only_for_marked():
    demo, cfg = build()
    ends = [d for d in cfg["dependencies"] if d["js"] and "wangpBusy?.end(\"apply\")" in d["js"]]
    assert len(ends) == 2 and all(d["trigger_only_on_success"] is False for d in ends)
    assert not any("t_other" in (d["js"] or "") for d in cfg["dependencies"])

def test_idempotent_config():
    demo, cfg1 = build()
    n = len(cfg1["dependencies"])
    assert len(demo.get_config_file()["dependencies"]) == n

def test_js_and_css_exist():
    assert "window.wangpBusy" in busy_states.get_javascript()
    assert ".wangp-busy" in busy_states.get_css()
```

- [ ] **Step 2: Run** `.venv\Scripts\python.exe -m pytest tests/test_busy_states.py -q -p no:cacheprovider` — Expected: FAIL (`ImportError`).
- [ ] **Step 3: Implement** `shared/gradio/busy_states.py` per Interfaces. The threshold timers in JS: `setTimeout(spinner, 150)`, `setTimeout(skeleton, 400)` if `opts.skeleton`, `setTimeout(() => end(key, {ok:false}), timeoutMs ?? 60000)` with a `console.warn`.
- [ ] **Step 4: Run** the same command — Expected: `4 passed`. Also re-run `tests/test_model_dropdowns_downloaded_only.py` — Expected: `6 passed`.
- [ ] **Step 5: Commit** `shared/gradio/busy_states.py` → `feat: add client-side busy layer with post-build event wiring`.

---

### Task 3: Model-switch start/end events

**Files:**
- Modify: `shared/gradio/gradio_model_change_queue.py:11-26` (the `_QUEUE_JS` string only)
- Modify: `shared/gradio/busy_states.py` (JS: model-switch listeners)
- Test: `tests/test_busy_states.py` (add tests)

**Interfaces:**
- Consumes: `window.wangpBusy.start/end` (Task 2).
- Produces: window events `wangp:model-switch-start` (dispatched in `wangpModelEnqueue` when a run is queued) and `wangp:model-switch-end` (dispatched in `wangpModelRelease` when the group's queue becomes empty).
- Produces (JS in busy_states): on `wangp:model-switch-start` → `wangpBusy.start("model", "#model_list", {skeleton: ".wangp-actions-column", timeoutMs: 120000})` and show a status line `Switching to <name>… rebuilding settings` (name = text of the last clicked `li.item` inside `#family_list, #model_base_types_list, #model_list`, else the current `#model_list input` value) inserted after the row containing `#family_list` (element id `wangp_switching_line`); on `wangp:model-switch-end` → `wangpBusy.end("model")` and hide the line.

- [ ] **Step 1: Write the failing tests** (append)

```python
from shared.gradio import gradio_model_change_queue as q

def test_queue_js_dispatches_switch_events():
    js = q._QUEUE_JS
    assert "wangp:model-switch-start" in js and "wangp:model-switch-end" in js
    assert js.index("wangp:model-switch-end") > js.index("function wangpModelRelease")

def test_queue_match_strings_unchanged():
    assert 'function Jt(S,J=null,K=null){' in q._REPLACEMENTS
    assert 'if(pe===void 0)return;const R=pe;' in q._REPLACEMENTS

def test_busy_js_listens_for_switch_events():
    js = busy_states.get_javascript()
    assert "wangp:model-switch-start" in js and "wangp:model-switch-end" in js
    assert ".wangp-actions-column" in js
```

- [ ] **Step 2: Run** `tests/test_busy_states.py` — Expected: 3 new FAIL.
- [ ] **Step 3: Implement**: in `_QUEUE_JS`, dispatch `window.dispatchEvent(new CustomEvent("wangp:model-switch-start"))` inside `wangpModelEnqueue` and `...-end` in `wangpModelRelease` in the branch where the queue is deleted. Add the listeners to `busy_states.get_javascript()`.
- [ ] **Step 4: Run** `tests/` — Expected: all pass (13 total).
- [ ] **Step 5: Commit** both files → `feat: signal model-switch start/end to the busy layer`.

---

### Task 4: Wire busy states into the app

**Files:**
- Modify: `wgp.py` (`create_ui` CSS/JS appends near `:14229` and `:14248`; one `mark_busy` line in `generate_media_tab` after `:13202` where `apply_lset_btn`, `refresh_lora_btn`, `refresh_lora_btn2`, `confirm_save_lset_btn`, `confirm_delete_lset_btn`, `save_settings_btn`, `reset_settings_btn`, `settings_file` all exist)
- Modify: `shared/gradio/model_selector_toolbar.py:39-40` (wrap `refresh_button`, `unload_button` with `mark_busy`)
- Modify: `plugins/configuration/plugin.py:806` (wrap `self.apply_btn` with `mark_busy(..., "config_save")`)
- Modify: `shared/gradio/gradio_engine_patch.py:74-78` (call `busy_states.install()` next to `gradio_model_change_queue.install()`)

**Interfaces:**
- Consumes: `mark_busy`, `install`, `get_css`, `get_javascript` (Task 2).
- Keys: `apply`, `refresh_loras`, `save_preset`, `delete_preset`, `set_default`, `reset_settings`, `load_settings`, `model_refresh`, `model_unload`, `config_save`.
- `wgp.py` lines: `css += "\n" + busy_states.get_css()` only when `UI_theme == "dark_clay"` (place after `UI_theme` is computed, `:14234`); `js += busy_states.get_javascript()`; one line of `mark_busy` calls (e.g. `for c, k in ((apply_lset_btn, "apply"), …): busy_states.mark_busy(c, k)`); `busy_states` added to the existing `from shared.gradio import …` at `:161`. Counts toward the ≤ 10-line budget (target 4 lines).

- [ ] **Step 1: Make the edits** listed above.
- [ ] **Step 2: Run** all tests — Expected: all pass.
- [ ] **Step 3: Restart UI and verify** with Playwright: navigate `http://localhost:7860`; evaluate `typeof window.wangpBusy` → `"object"`; click **Apply** (preset row) and within 2 s evaluate that the button got then lost `wangp-busy` (poll every 50 ms via `browser_evaluate` returning a class timeline); click toolbar ↻ and confirm the same; trigger a failing action (first try Apply with no preset selected; if that shows no error toast, evaluate `window.wangpBusy.start("probe", "#wangp_model_tool_refresh")`, inject a `.toast-body.error` element into `body`, then `window.wangpBusy.end("probe")`) and confirm `wangp-busy` clears and `wangp-busy-done` (✓) does **not** appear; console has no new errors besides `manifest.json` 404.
- [ ] **Step 4: Commit** the four modified files → `feat: show busy states on preset, settings, toolbar and config actions`.

---

### Task 5: Model capabilities in the UI (dimming + unload)

**Files:**
- Modify: `wgp.py` (≤ 3 lines: create `model_caps = gr.Textbox(value=capabilities_payload(get_model_name(transformer_type), get_model_def(transformer_type)), visible=False, elem_id="wangp_model_caps")` inside `generate_media_tab` near `gen_status` `:13235`; return its update from `switch_model_form` `:13802` and add it to its outputs `:13807`)
- Modify: `shared/gradio/busy_states.py` (JS + CSS for dimming)
- Test: `tests/test_busy_states.py` (add)

**Interfaces:**
- Consumes: `capabilities_payload` (Task 1).
- `switch_model_form` appends `capabilities_payload(get_model_name(mt), get_model_def(mt))` with `mt = get_state_model_type(state_value)`; outputs list appends `model_caps`. The hidden textbox lives in both Generate and Edit builds; only the Generate tab's `switch_model_form` returns it (Edit tab has no model switch).
- JS: observe `#wangp_model_caps textarea` value (MutationObserver on the element + `input` events + initial read); parse JSON; for each top-level tab button whose trimmed text is `Mask Generator` (cap `mask`) or `Motion Designer` (cap `motion`), and each gallery tab button `Video / Images` (`video || image`), `Audio Files` (`audio`), `3D` (`mesh`): toggle class `wangp-na` and attribute `data-wangp-tip="Not used by <model_name>"`.
- JS: ⏏ unload (`#wangp_model_tool_unload`) gets `wangp-na` + `aria-disabled="true"` while the `gen_status` text contains `No Model is Loaded` (MutationObserver on the status component's root, located as the element containing that text inside `.wangp-progress`).
- CSS: `.wangp-na { opacity:.38; cursor:help }`, tooltip from `[data-wangp-tip]:hover::after` styled like the mockup.

- [ ] **Step 1: Write the failing test**

```python
def test_dimming_js_targets_expected_tabs():
    js = busy_states.get_javascript()
    for label in ("Mask Generator", "Motion Designer", "Video / Images", "Audio Files", "3D", "wangp_model_caps", "Not used by "):
        assert label in js
    assert ".wangp-na" in busy_states.get_css()
```

- [ ] **Step 2: Run** — Expected: FAIL.
- [ ] **Step 3: Implement** JS/CSS and the `wgp.py` lines.
- [ ] **Step 4: Run** tests — Expected: all pass. Restart UI; with Playwright: initial model Wan2.1 Text2video 14B → `Mask Generator`, `Motion Designer`, `Audio Files`, `3D` have `wangp-na`; switch family to a Flux image model → `Video / Images` enabled, `Audio Files` dimmed; switch to an ACE-Step model → `Audio Files` enabled, `Video / Images` dimmed; hover tooltip text equals `Not used by <name>`; ⏏ has `aria-disabled="true"`.
- [ ] **Step 5: Commit** → `feat: dim tabs and tools the selected model cannot use`.

---

### Task 6: Page skeleton & gallery placeholders

**Files:**
- Modify: `shared/gradio/busy_states.py` (add `get_head_html() -> str`, gallery observer JS, gallery CSS)
- Modify: `wgp.py:14267` (pass `head=busy_states.get_head_html() if UI_theme == "dark_clay" else None` to `ui_studio.Blocks(...)`; 0 extra lines if done inline)
- Test: `tests/test_busy_states.py` (add)

**Interfaces:**
- `get_head_html()` returns `<style>` + `<div id="wangp_page_skeleton">…</div>` markup + `<script>` that: inserts the skeleton as the first child of `body` on `DOMContentLoaded`; removes it with a 250 ms opacity fade once `document.querySelector("#family_list")` exists (poll every 100 ms via `requestAnimationFrame`/`setInterval`), or after 20 000 ms regardless. Layout per mockup section 4 (title bar, selector row, two columns). Background `#22232f`, `position:fixed; inset:0; z-index:9999`.
- Gallery JS: a MutationObserver adds `wangp-media-loading` to `.wangp-studio-gallery` thumbnails whose `img` is not `complete` or `video.readyState < 2`, removed on `load`/`loadeddata`/`error`. CSS: shimmer like `.sk`.

- [ ] **Step 1: Write the failing test**

```python
def test_head_html_has_skeleton_and_self_removal():
    html = busy_states.get_head_html()
    assert 'id="wangp_page_skeleton"' in html and "#family_list" in html and "20000" in html
```

- [ ] **Step 2: Run** — FAIL. **Step 3: Implement.** **Step 4: Run** tests — pass. Restart UI; Playwright: navigate and screenshot within 300 ms of `goto` (`waitUntil: "commit"` via `browser_run_code_unsafe` or immediate screenshot) → skeleton visible; after load `document.getElementById("wangp_page_skeleton")` is null.
- [ ] **Step 5: Commit** → `feat: add Dark Clay page skeleton and gallery placeholders`.

---

### Task 7: Progress restyle, switch-preload downloads, small fixes

**Files:**
- Modify: `shared/gradio/ui_studio_dark_clay.css` (WangpProgress + status card, tab underline, info icon)
- Modify: `wgp.py:11111` (add `gen=gen,` to the `load_models(...)` call in `preload_model_when_switching`)

**Interfaces:**
- CSS targets: `.wangp-progress` and its existing variables (`shared/gradio/progress.py:178-187` declares them; override the `_dark` values' resulting custom properties under `.dark .wangp-progress`) → clay status card: surface `#2c2d3c`, radius 18 px, puff shadow, bar track `--clay-dent`, determinate fill `linear-gradient(90deg,#7f6cf5,#9b8cff,#b8adff)`, download fill `linear-gradient(90deg,#e0a040,#ffc46b)`.
- Tab underline: `.tab-container::after { display:none }` for all tabs under Dark Clay.
- Info icon: the blue `ⓘ` elements (find via Playwright `getComputedStyle(...).color` in the blue range on the running page) → `color: var(--studio-accent)`.

- [ ] **Step 1: Make the edits.**
- [ ] **Step 2: Verify** with Playwright: screenshot the status panel idle; force a progress render by evaluating a call that sets the `.wangp-progress` element into its download mode if a demo hook exists, otherwise check computed styles of `.wangp-progress` (border-radius `18px`, background `rgb(44, 45, 60)`); full-page screenshot shows no full-width 1 px line; no blue `ⓘ` remains (evaluate count of visible elements with color `rgb(37, 99, 235)`/`rgb(53, 127, 196)` → 0).
- [ ] **Step 3: Verify the preload fix** by reading the call site: `load_models(model_type, output_type=…, override_compile=…, gen=gen)`; run all tests — pass.
- [ ] **Step 4: Commit** → `feat: clay progress panels, report switch downloads, remove tab underline`.

---

### Task 8: End-to-end verification & push

**Files:** none (verification only), unless fixes are needed (commit them separately).

- [ ] **Step 1: Model-switch timing** — Playwright: 5 switches between `Text2video 14B` and `Text2video 1.3B`, measuring time from option click until `#model_list input` shows the new name and the settings column stops changing for 200 ms (MutationObserver idle). Run once on a worktree of commit `bca97169` (baseline: `git worktree add ..\wgp-baseline bca97169`, run its `wgp.py` on port 7861 with the same `.venv` and a copy of `run_ui_cpu.py`) and once on the branch head. Pass: median regression ≤ 50 ms. Remove the worktree afterwards (`git worktree remove ..\wgp-baseline`).
- [ ] **Step 2: Review-focus checks** — (a) double-click a model option twice quickly: one spinner, cleared once; (b) theme `default` (`wgp_config.json` `UI_theme`), restart: no `.wangp-busy` styles, no page skeleton, no new console errors; restore `dark_clay`; (c) stop the server mid-switch: spinner clears within the safety timeout or on connection failure.
- [ ] **Step 3: Screenshots** of each state vs. mockup sections 1–5; note any visible mismatch and fix or list it.
- [ ] **Step 4: Run** all tests — pass. `git log --oneline` shows Tasks 1–7 commits; `git diff bca97169 --stat -- wgp.py` shows ≤ 10 changed lines.
- [ ] **Step 5: Push** `git -c credential.helper= -c "credential.helper=!gh auth git-credential" push` (branch `feature/dark-clay-ui`, already tracking origin).
