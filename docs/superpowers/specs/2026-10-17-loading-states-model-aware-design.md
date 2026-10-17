# Loading states & model-aware UI — design

- **Date:** 2026-10-17
- **Branch:** `feature/dark-clay-ui`
- **Status:** approved in conversation (visual design + technical design); awaiting spec review
- **Mockup:** `.superpowers/brainstorm/1081-1792220591/content/loading-states.html` (local only)

## Goal

1. Every action that takes noticeable time shows a loading state, in the Dark Clay style.
2. UI parts the selected model cannot use are visibly marked, everywhere, without hiding them.

## Background (current behavior)

- A model switch re-runs the whole form builder (`generate_media_tab(update_form=True)` via `fill_inputs`) and returns ~320 `gr.update`s. The settings panel already adapts to ~85 `model_def` keys; that system stays as is.
- 211 event handlers use `show_progress="hidden"`. Outside generation (`WangpProgress`, `refresh_status_async`) and Enhance Prompt (`WangpProgress.bind`), nothing indicates work in progress.
- Not model-aware today: top plugin tabs (Mask Generator, Motion Designer), gallery tabs (Video/Images, Audio Files, 3D), toolbar ⏏ Unload.
- `gradio_model_change_queue.py` registers a frontend-only "ack" continuation (`js='()=>{}'`) after the model-switch tail (`switch_model_form`). The patched Gradio bundle fires the ack on success, on `stage === "error"`, and on connection failure.
- Model preload on switch (`preload_model_when_switching`, `wgp.py:~11099`) calls `load_models` without `gen`, so downloads it triggers only show "Loading...".

## Interaction rules (apply everywhere)

| Elapsed since action start | Shown |
|---|---|
| < 150 ms | nothing (no flicker) |
| ≥ 150 ms | spinner on the triggering control, control pressed + inert |
| ≥ 400 ms | skeleton/dim on the affected region (model switch only) |
| on success (button actions > 150 ms) | ✓ for 900 ms |
| on error | busy state cleared; existing Gradio error toast shows |
| safety timeout (default 60 s, per key overridable) | busy state force-cleared, `console.warn` |

Buttons keep their label while busy (spinner replaces the icon) so widths never jump. Reduced-motion users get static indicators (no spin/shimmer animation).

## Components

### 1. `shared/gradio/busy_states.py` (new)

- `get_css()` / `get_javascript()` — appended in `create_ui` like the other modules.
- JS API on `window.wangpBusy`:
  - `start(key, targetSelector, {skeleton: selector?, timeoutMs?})` — schedules spinner at 150 ms and skeleton at 400 ms; tracks keys so overlapping starts of the same key are idempotent.
  - `end(key, {ok = true})` — cancels pending timers, removes classes, shows ✓ when `ok` and the spinner had appeared.
  - Classes applied: `.wangp-busy` (control), `.wangp-busy-done` (✓), `.wangp-skeleton` (region overlay).
- Python helper `bind_busy(listener_fn, key, target, **event_kwargs)`:
  - Calls the Gradio event (e.g. `button.click`) with `js="(...a) => { window.wangpBusy?.start(KEY, TARGET); return a; }"` so the spinner starts client-side before the request.
  - Chains `.then(fn=None, js="() => window.wangpBusy?.end(KEY)")`, which runs after success or failure.
  - Returns the original dependency so existing `.then` chains keep working.
- Applied to: Lora preset **Apply / Save / Delete (confirm) / Refresh**, **Set Settings as Default**, **Reset Settings**, **Load settings file**, toolbar **Refresh** and **Unload**, Configuration **Save Settings**.
- Not wrapped (already have busy UIs, restyled only): **Generate / Add to queue** (button swap), **Enhance Prompt** (`WangpProgress.bind`).

### 2. Model-switch loading

- **Start (client):** delegated listeners in `busy_states` JS call `wangpBusy.start('model', '#model_list', {skeleton: <settings column>})` on: option selection inside `#family_list`, `#model_base_types_list`, `#model_list`; output-filter icon clicks; downloaded-only toggle; model search panel apply. Also shows a "Switching to <name>…" line under the selector row (text from the clicked option).
- **End:** in `gradio_model_change_queue.py`, the ack continuation's `js='()=>{}'` becomes `js='()=>{window.wangpBusy?.end("model")}'`. Because the ack fires on success, error and connection failure, the skeleton always clears.
- While skeletoned, the settings column is `pointer-events: none` (input typed mid-rebuild would be overwritten anyway).

### 3. Generation & downloads

- Restyle `WangpProgress` (`shared/gradio/progress.css` values via Dark Clay overrides in `ui_studio_dark_clay.css`) and the `gen_status` panel to match the mockup's status card: pulsing state dot, title/subtitle, clay progress bar (determinate, indeterminate, download colors), meta line.
- Functional fix: `preload_model_when_switching` passes the active `gen` to `load_models` so switch-triggered downloads report bytes/speed/files through the existing `download_progress` mechanism.
- Out of scope here (Phase B): step strip, RAM/VRAM chips, new live-preview treatment, ETA — unless the data is already rendered by `WangpProgress`, in which case it is only restyled.

### 4. Page & gallery load

- Page skeleton: HTML + CSS + a small script passed through Gradio's `head=` parameter on the `ui_studio.Blocks(...)` call (no change to `gradio_frontend_patch`), rendering a clay skeleton of the WanGP layout; removed with a 250 ms fade once `#family_list` (or the main tabs) exists in the DOM, with a 20 s fallback removal.
- Only active when the Dark Clay theme is selected (other themes keep Gradio's loader).
- Gallery: CSS placeholder shimmer on gallery thumbnails while their media has not loaded (`img`/`video` without `complete`/`readyState`), via a class toggled by a small observer.

### 5. Model capabilities — `shared/model_capabilities.py` (new)

- `get_model_capabilities(model_def: dict) -> dict` — pure function, no Gradio import:
  - `mask`: model uses masks/guides from Mask Generator (`mask_preprocessing` or `guide_preprocessing` non-empty, or `image_ref_choices` present).
  - `motion`: Motion Designer is usable — mirrors the predicate in `plugins/motion_designer/plugin.py:176-187` (`i2v_v2v`, `vace_class`, `i2v_trajectory`). The plugin is not modified; the copy carries a comment pointing at the plugin lines, and a test asserts both agree on the sample model definitions.
  - `video`, `image`, `audio`, `mesh`: from `image_outputs`, `audio_only`, `mesh_outputs` (video = not image-only/audio-only/mesh).
- Delivery: one hidden `gr.JSON`/`gr.Textbox` (`elem_id="wangp_model_caps"`) holding `{"model_name": ..., "caps": {...}}`, initial value set at build time, appended as **one** extra output of `switch_model_form` only. Capabilities depend solely on the model definition, not on image mode or settings, so `fill_inputs` refresh paths (image-mode tabs, reset, presets) do not update it.
- Client: the `busy_states` JS reads the JSON on change and toggles `.wangp-na` + `data-wangp-tip="Not used by <name>"` on:
  - top tabs "Mask Generator", "Motion Designer" (matched by tab label text);
  - gallery tabs "Video / Images" (video or image), "Audio Files" (audio), "3D" (mesh).
- `.wangp-na`: opacity 0.38, `cursor: help`, tooltip on hover; still clickable.
- ⏏ Unload: disabled (`.wangp-na` + `aria-disabled`) while `gen_status` reads "No Model is Loaded" — client observes the existing 0.5 s idle-status refresh; no new server output.

### 6. Small fixes

- Hide Gradio's `.tab-container::after` 1px underline for all tabs under Dark Clay (the full-width line).
- Recolor the blue info (ⓘ) icons to the theme accent.

## `wgp.py` footprint

Target ≤ 10 changed lines: busy/capabilities CSS+JS appends, `bind_busy` at the listed call sites (or equivalent post-hoc wiring from the helper module), the caps component + one output, the preload `gen` argument.

## Error handling

- Every `start` has an `end` path on success and failure; the safety timeout covers anything missed (e.g. a handler that never returns).
- If `window.wangpBusy` is missing (other themes, script error), all hooks are no-ops via optional chaining — the app behaves exactly as today.
- Capability computation failures (unexpected `model_def`) return all-true caps (nothing dimmed) and log once.

## Testing

- `pytest` (local `tests/`, gitignored in this repo):
  - `get_model_capabilities` against real definitions from `defaults/*.json` (a T2V, an image model, an audio model, a Vace model, a 3D model) plus missing-key/empty dicts.
  - `bind_busy` builds the expected `js` strings and returns the dependency.
- Playwright against the running UI:
  - model switch: `.wangp-busy` on `#model_list` appears after 150 ms and clears after the ack; skeleton appears for slow switches; forced server error still clears it.
  - each wrapped button: busy → ✓ → idle.
  - caps: switching T2V ↔ image ↔ audio model dims the expected tabs; tooltip text correct.
  - page skeleton shows on reload and is removed.
  - screenshots compared with the mockup.
- Timing: model-switch duration before/after (median of 5) must not regress by more than ~50 ms.

## Out of scope

Layout restructuring ("Phase B"): ⚙ config button, two-column sliders, collapsed advanced settings, RAM/VRAM chips, search inside model menus, step strip, ETA.
