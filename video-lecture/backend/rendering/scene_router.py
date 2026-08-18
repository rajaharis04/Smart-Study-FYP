# -*- coding: utf-8 -*-
"""
SmartStudyInstructor V10 — Scene Router (DNA-Aware)
Routes Blueprint scenes to dedicated Jinja2 templates based on DNA types.
Embeds window.TIMELINE_DATA and window.DIAGRAM_DATA for GSAP/Fabric timelines.
"""
import os
import json
import jinja2
from typing import Dict, Optional
from app.utils.logger import log_info, log_error

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")

# Map of the 8 Scene DNA archetypes to Jinja2 template files
# concept.html.j2 is the unified layout for most types; specialized templates used where they add value
DNA_TEMPLATE_MAP = {
    "DNA-1 CONCEPT_DEFINITION": "concept.html.j2",
    "DNA-2 PROCESS_FLOW": "concept.html.j2",
    "DNA-3 CAUSE_EFFECT": "concept.html.j2",
    "DNA-4 COMPARISON": "concept.html.j2",
    "DNA-5 DIAGRAM_SPATIAL": "concept.html.j2",
    "DNA-6 WORKED_EXAMPLE": "concept.html.j2",
    "DNA-7 ANALOGY_BRIDGE": "concept.html.j2",
    "DNA-8 TAKEAWAY_SUMMARY": "takeaway_summary_scene.html.j2"
}

# Avatar configuration parameters per layout
AVATAR_CONFIGS = {
    "concept_definition": {"size": 180, "ring": "#C9B99A", "visible": True},
    "process_flow": {"size": 120, "ring": "#4F8EF7", "visible": True},
    "cause_effect": {"size": 140, "ring": "#FF3B3B", "visible": True},
    "comparison": {"size": 140, "ring": "#FFD700", "visible": True},
    "diagram_spatial": {"size": 120, "ring": "#00E5FF", "visible": True},
    "worked_example": {"size": 130, "ring": "#FFD700", "visible": True},
    "analogy_bridge": {"size": 150, "ring": "#C9B99A", "visible": True},
    "takeaway_summary": {"size": 320, "ring": "#0C1223", "visible": True}
}

class SceneRouter:
    """Routes DNA-grounded blueprint scenes to dedicated templates."""

    def __init__(self, template_dir: str = None):
        tdir = template_dir or TEMPLATE_DIR
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(tdir),
            autoescape=False
        )
        
        # Word wrap filter for sequential karaoke dim reveals
        import re
        def wordwrap_spans(text):
            if not text:
                return ""
            parts = re.split(r'(<[^>]+>)', text)
            result = []
            for part in parts:
                if part.startswith('<') and part.endswith('>'):
                    result.append(part)
                else:
                    words_and_spaces = re.split(r'(\s+)', part)
                    wrapped_part = []
                    for item in words_and_spaces:
                        if not item:
                            continue
                        if item.isspace():
                            wrapped_part.append(item)
                        else:
                            wrapped_part.append(f'<span class="word-span">{item}</span>')
                    result.append("".join(wrapped_part))
            return "".join(result)
            
        self.jinja_env.filters["wordwrap_spans"] = wordwrap_spans

    def select_dna_template(self, scene: Dict) -> str:
        """Determines the correct Jinja2 template based on the Scene DNA type."""
        dna_dict = scene.get("scene_dna") or {}
        dna_type = dna_dict.get("dna_type", "")
        
        template = DNA_TEMPLATE_MAP.get(dna_type)
        if not template:
            # Fallback legacy layout mapping
            legacy_type = scene.get("scene_type", "concept")
            if legacy_type == "formula":
                template = "worked_example_scene.html.j2"
            elif legacy_type == "table":
                template = "comparison_scene.html.j2"
            elif legacy_type == "process":
                template = "process_flow_scene.html.j2"
            elif legacy_type == "summary":
                template = "takeaway_summary_scene.html.j2"
            else:
                template = "concept_definition_scene.html.j2"

        # Verify template exists on disk
        target_path = os.path.join(self.jinja_env.loader.searchpath[0], template)
        if not os.path.exists(target_path):
            log_error(f"[SceneRouter] Target template not found on disk: {target_path}. Using fallback.")
            return "concept_definition_scene.html.j2"

        return template

    def render_scene_html(self, scene: Dict, timeline_data: Dict = None) -> str:
        """Renders the Jinja2 HTML layout with TIMELINE_DATA variables injected."""
        template_name = self.select_dna_template(scene)
        
        dna_dict = scene.get("scene_dna") or {}
        preset = dna_dict.get("layout_preset", "concept_definition")
        # Merge: DNA-specific defaults (size, ring) + pipeline runtime flags (hidden_for_ffmpeg, is_lipsync)
        dna_defaults = AVATAR_CONFIGS.get(preset, AVATAR_CONFIGS["concept_definition"]).copy()
        pipeline_overrides = scene.get("avatar_config") or {}
        avatar_config = {**dna_defaults, **pipeline_overrides}

        tdata = timeline_data or {
            "scene_id": scene.get("scene_id"),
            "total_duration_ms": scene.get("duration_sec", 10) * 1000,
            "events": [],
        }

        try:
            template = self.jinja_env.get_template(template_name)

            # ── Avatar auto-hide for diagram-heavy DNA types ──
            _dna_type = (dna_dict.get("dna_type") or "").upper()
            _layout_preset = (dna_dict.get("layout_preset") or "").lower()
            hide_avatar = (
                any(t in _dna_type for t in ["DIAGRAM_SPATIAL", "PROCESS_FLOW", "CAUSE_EFFECT", "WORKED_EXAMPLE"]) or
                any(p in _layout_preset for p in ["diagram_spatial", "process_flow", "cause_effect", "worked_example"])
            )

            # ── V16: Scene mode context variables ──
            _scene_mode = scene.get("scene_mode", "bullets_only")
            # show_bullets: only when the scene actually HAS bullets AND mode allows them
            _has_bullets = bool(scene.get("bullets"))
            _show_bullets = _has_bullets and _scene_mode in ("bullets_only", "bullets_then_diagram")
            # show_diagram: true when the scene has a programmatic SVG or diagram references
            _has_diagram_asset = bool(
                scene.get("_programmatic_svg")
                or scene.get("diagram_refs")
                or scene.get("diagram_paths")
            )
            _show_diagram = _has_diagram_asset or (_scene_mode in ("diagram_only", "bullets_then_diagram"))
            _diagram_fullscreen = (_scene_mode == "diagram_only")
            # show_left_panel: the navy left panel is fully absent for diagram_only scenes
            _show_left_panel = not _diagram_fullscreen

            # Also hide avatar for diagram_only scenes
            if _diagram_fullscreen:
                hide_avatar = True


            html = template.render(
                scene=scene,
                avatar_config=avatar_config,
                timeline_data=tdata,
                word_timestamps=tdata.get("word_timestamps", []),
                hide_avatar=hide_avatar,
                scene_audio_duration_ms=int(tdata.get("total_duration_ms", 45000)),
                # V16: Scene mode layout control
                show_left_panel=_show_left_panel,
                show_bullets=_show_bullets,
                show_diagram=_show_diagram,
                diagram_fullscreen=_diagram_fullscreen,
                scene_mode=_scene_mode,

            )
            return html
        except Exception as e:
            log_error(f"[SceneRouter] Render failed ({template_name}): {e}")
            return ""
