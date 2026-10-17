# Copyright (c) 2026 DeepBeepMeep - part of WanGP, WanGP Community License 2.0 (see LICENSE.txt)
"""Capability flags derived from a model definition, used to dim UI parts a model cannot use.

Pure stdlib helper: no Gradio dependency.
"""

from __future__ import annotations

import json

CAPABILITY_KEYS = ("mask", "motion", "video", "image", "audio", "mesh")

_warned_inputs: set[str] = set()


def _selection_used(entry) -> bool:
    if not isinstance(entry, dict) or entry.get("visible", True) is False:
        return False
    selection = entry.get("selection")
    if not isinstance(selection, list):
        return False
    return any(isinstance(choice, str) and choice != "" for choice in selection)


def get_model_capabilities(model_def: dict | None) -> dict[str, bool]:
    try:
        if not isinstance(model_def, dict):
            raise TypeError("model definition is not a dict")
        image = bool(model_def.get("image_outputs"))
        audio = bool(model_def.get("audio_only"))
        mesh = bool(model_def.get("mesh_outputs"))
        mask = (
            _selection_used(model_def.get("mask_preprocessing"))
            or _selection_used(model_def.get("guide_preprocessing"))
            or _selection_used(model_def.get("image_ref_choices"))
        )
        # mirrors plugins/motion_designer/plugin.py:176-187 (on_tab_select)
        motion = any(bool(model_def.get(key)) for key in ("i2v_v2v", "vace_class", "i2v_trajectory"))
        return {
            "mask": mask,
            "motion": motion,
            "video": not (image or audio or mesh),
            "image": image,
            "audio": audio,
            "mesh": mesh,
        }
    except Exception as exc:
        key = repr(model_def)[:200]
        if key not in _warned_inputs:
            _warned_inputs.add(key)
            print(f"[model_capabilities] malformed model definition {key} ({exc}); enabling all capabilities")
        return dict.fromkeys(CAPABILITY_KEYS, True)


def capabilities_payload(model_name: str, model_def: dict | None) -> str:
    return json.dumps({"model_name": model_name, "caps": get_model_capabilities(model_def)})
