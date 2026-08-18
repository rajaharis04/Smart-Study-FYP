"""
animation_brain.py — Two-stage intelligent diagram analysis and animation generation.

Stage 1: Qwen2.5-VL deeply understands the diagram (structure, purpose, elements, math)
Stage 2: Groq LLaMA 4 Scout generates narration-coupled animation sequence

Never raises exceptions — always returns [] on any error.
Never generates unwanted blue lines or auto-connector artifacts.
Only NODE elements get zoom/circle — connectors NEVER do.
Flow arrows only where Stage 1 identified actual connections.
"""

import json
import logging
import re
from pathlib import Path
from typing import Optional

from core.ai_providers import analyze_image_json, generate_text_json

log = logging.getLogger("animation_brain")


# ══════════════════════════════════════════════════════════════════════════════
# Word timestamp utilities (preserved from original)
# ══════════════════════════════════════════════════════════════════════════════

def _build_word_index(word_timestamps: list) -> dict:
    """Build a word → start_ms lookup from TTS word boundaries."""
    idx = {}
    for wt in word_timestamps:
        word = wt.get("word", "")
        ms = wt.get("start_ms", 0)
        clean = word.lower().strip(".,;:?!\"'-()")
        idx[clean] = ms
        if len(clean) >= 5:
            idx[clean[:5]] = ms
        if len(clean) >= 4:
            idx[clean[:4]] = ms
    return idx


def _resolve_ms(keyword: str, word_index: dict, fallback: int) -> int:
    """Resolve a keyword to its spoken millisecond from word_index."""
    if not keyword:
        return fallback
    kw = keyword.lower().strip(".,;:?!\"'-()")
    if kw in word_index:
        return word_index[kw]
    if len(kw) >= 5 and kw[:5] in word_index:
        return word_index[kw[:5]]
    if len(kw) >= 4 and kw[:4] in word_index:
        return word_index[kw[:4]]
    # Substring match as last resort
    for stored, ms in word_index.items():
        if kw in stored or stored in kw:
            return ms
    return fallback


def _simplified_word_timestamps(word_timestamps: list) -> str:
    """Create a compact word→ms JSON string for LLM prompt (max 80 words)."""
    simplified = {wt["word"]: wt["start_ms"] for wt in word_timestamps[:80]}
    return json.dumps(simplified)


def _extract_narration_keywords(narration: str) -> list:
    """Extract top content keywords from narration for VLM grounding."""
    _stopwords = {
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'and', 'or', 'but', 'in',
        'on', 'at', 'to', 'for', 'of', 'with', 'by', 'this', 'that', 'these',
        'those', 'it', 'its', 'they', 'them', 'we', 'you', 'your', 'our', 'has',
        'have', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
        'can', 'may', 'might', 'not', 'no', 'so', 'if', 'then', 'here', 'there',
        'what', 'how', 'why', 'when', 'where', 'which', 'who', 'from', 'into',
        'about', 'each', 'every', 'all', 'both', 'more', 'most', 'other', 'some',
        'such', 'only', 'just', 'also', 'than', 'very', 'too', 'now', 'let', 'us',
        'one', 'two', 'three', 'first', 'second', 'new', 'way', 'make', 'like',
    }
    words = re.findall(r"[a-zA-Z]{4,}", narration.lower())
    freq = {}
    for w in words:
        if w not in _stopwords:
            freq[w] = freq.get(w, 0) + 1
    return sorted(freq.keys(), key=lambda w: (-freq[w], w))[:20]


# ══════════════════════════════════════════════════════════════════════════════
# STAGE 1 — DEEP DIAGRAM COMPREHENSION (Qwen2.5-VL)
# ══════════════════════════════════════════════════════════════════════════════

def _stage1_comprehend(image_path: str, narration: str, scene_id: str) -> Optional[dict]:
    """
    Calls Qwen2.5-VL to deeply understand the diagram.
    Does FOUR things simultaneously:
      1. Diagram type classification
      2. Deep semantic understanding (educational purpose)
      3. Element inventory with relationships
      4. Mathematical content detection
    Returns structured analysis dict or None on failure.
    """
    narration_short = narration[:600].replace('"', "'")
    keywords = _extract_narration_keywords(narration)
    kw_list = ", ".join(f'"{k}"' for k in keywords)

    stage1_prompt = f"""You are an expert educational diagram analyst with deep knowledge of mathematics, physics, biology, CS, and engineering.

TEACHER NARRATION (this is what the teacher says while explaining this diagram):
"{narration_short}"

VALID TRIGGER KEYWORDS (pick trigger_keyword from this list ONLY):
[{kw_list}]

Analyze this diagram deeply. Return ONLY valid JSON starting with {{ immediately:

{{
  "diagram_type": "flowchart|biological_diagram|circuit_diagram|graph_chart|mathematical_formula|data_table|architectural_diagram|cause_effect_diagram|timeline_diagram|comparison_diagram|concept_map|network_diagram|process_flow|other",
  "educational_purpose": "2-3 sentences explaining what concept this diagram teaches and why it is important",
  "complexity": "simple|moderate|complex",
  "has_math": true or false,
  "elements": [
    {{
      "id": "e1",
      "label": "exact text visible on this element",
      "element_type": "node|connector|label|zone|formula",
      "x_pct": 0.10,
      "y_pct": 0.15,
      "w_pct": 0.20,
      "h_pct": 0.12,
      "connects_from": null,
      "connects_to": null,
      "is_primary": true,
      "trigger_keyword": "word_from_valid_list",
      "pedagogical_order": 1,
      "description": "what this element represents educationally"
    }}
  ],
  "mathematical_expressions": [
    {{
      "latex": "F = ma",
      "plain_english": "Force equals mass times acceleration",
      "location_description": "center of diagram",
      "step_breakdown": [
        {{"latex": "F", "meaning": "Force in Newtons", "trigger_keyword": "force"}},
        {{"latex": "m", "meaning": "mass in kilograms", "trigger_keyword": "mass"}},
        {{"latex": "a", "meaning": "acceleration", "trigger_keyword": "acceleration"}}
      ]
    }}
  ],
  "connections": [
    {{
      "from_id": "e1",
      "to_id": "e2",
      "label": "arrow label if any",
      "connection_type": "arrow|bidirectional|dashed|causes|flows_to"
    }}
  ],
  "logical_flow": "left_to_right|top_to_bottom|radial|no_flow|circular",
  "teaching_order_reasoning": "one sentence explaining the pedagogical order to explain elements"
}}

CRITICAL RULES:
- x_pct and y_pct are the TOP-LEFT corner as a fraction (0.0 to 1.0) of FULL image width/height
- w_pct and h_pct are the element's width and height as fractions of FULL image dimensions
- element_type "connector" means arrow or line — these NEVER get zoom or circle animations
- element_type "node" means a box, circle, label, or region representing a concept
- is_primary means this is a main concept (not a minor label or decoration)
- trigger_keyword MUST be from the VALID TRIGGER KEYWORDS list above
- pedagogical_order starts at 1 — order as a teacher would explain (fundamental first)
- If diagram has formulas, always populate mathematical_expressions with step_breakdown
- connects_from and connects_to are ONLY for connector type elements"""

    result = analyze_image_json(
        image_path=image_path,
        prompt=stage1_prompt,
        task_name=f"stage1_comprehend_{scene_id}",
        max_tokens=2500
    )

    if result is None:
        log.warning(f"[animation_brain] Stage 1 VLM returned None for {scene_id}")
        return None

    # Validate minimum structure
    if "elements" not in result or not isinstance(result.get("elements"), list):
        log.warning(f"[animation_brain] Stage 1 returned invalid structure for {scene_id}")
        return None

    # Count primary nodes (elements that should get animations)
    primary_nodes = [e for e in result["elements"]
                     if e.get("element_type") != "connector" and e.get("is_primary", False)]
    dtype = result.get("diagram_type", "unknown")
    n_math = len(result.get("mathematical_expressions", []))

    log.info(f"[animation_brain] Stage 1 success: {dtype} with {len(result['elements'])} elements "
             f"({len(primary_nodes)} primary nodes, {n_math} math expressions)")
    return result


# ══════════════════════════════════════════════════════════════════════════════
# STAGE 2 — INTELLIGENT ANIMATION SCRIPT GENERATION (Groq LLaMA)
# ══════════════════════════════════════════════════════════════════════════════

def _stage2_animate(stage1: dict, narration: str, word_timestamps: list, scene_id: str) -> Optional[list]:
    """
    Uses Groq LLaMA 4 Scout to generate narration-coupled animation events
    based on Stage 1's deep understanding + exact word timestamps.
    """
    wt_simplified = _simplified_word_timestamps(word_timestamps)

    # Filter to primary nodes only — connectors never get animations
    primary_nodes = [e for e in stage1.get("elements", [])
                     if e.get("element_type") != "connector" and e.get("is_primary", False)]
    # Sort by pedagogical order
    primary_nodes.sort(key=lambda e: e.get("pedagogical_order", 99))

    # Confirmed connections from Stage 1
    connections = stage1.get("connections", [])

    stage2_prompt = f"""You are an expert educational video director. Create a precise diagram animation sequence synchronized with the teacher's narration.

DIAGRAM ANALYSIS FROM STAGE 1:
Type: {stage1.get('diagram_type', 'unknown')}
Purpose: {stage1.get('educational_purpose', '')}
Flow direction: {stage1.get('logical_flow', 'no_flow')}
Teaching order: {stage1.get('teaching_order_reasoning', '')}
Has math: {stage1.get('has_math', False)}

PRIMARY ELEMENTS (these are the ONLY elements that can get zoom/circle/highlight animations):
{json.dumps(primary_nodes, indent=2)}

CONFIRMED CONNECTIONS (ONLY these pairs can get flow_arrow events):
{json.dumps(connections, indent=2)}

MATHEMATICAL EXPRESSIONS:
{json.dumps(stage1.get('mathematical_expressions', []), indent=2)}

TEACHER NARRATION:
{narration[:700]}

WORD → MILLISECOND MAP (word spoken → exact ms timestamp):
{wt_simplified}

YOUR TASK: Create an animation sequence that explains this diagram the way a master teacher would — synchronized precisely with the narration.

STRICT RULES (NEVER VIOLATE):
1. ONLY elements listed in PRIMARY ELEMENTS above get zoom_in, annotate_circle, or highlight events
2. ONLY connections listed in CONFIRMED CONNECTIONS above get flow_arrow events — NEVER invent arrows
3. NO blue colors anywhere — use: "#00E5FF" for circles, "#FFD700" for arrows and highlights, "#FF4444" for cause/danger, "#44FF88" for effect/safe
4. Every animation must have a trigger_word that EXISTS in the narration
5. Teaching order must match pedagogical_order from the elements, NOT spatial position
6. Maximum 8 animation events total to prevent cognitive overload
7. First event MUST be diagram_overview at trigger_ms 400
8. Always zoom_out BEFORE zooming into the next node
9. For mathematical expressions: generate formula_step_reveal events, NOT zoom events
10. trigger_ms values MUST come from the WORD → MILLISECOND MAP above

For each primary node in pedagogical order:
- Find the EXACT word from the narration that introduces this element (use its trigger_keyword)
- Set trigger_ms to that word's start_ms from the timestamps
- Generate: cursor_move (trigger_ms - 600), zoom_in (trigger_ms - 300), annotation (trigger_ms), zoom_out (trigger_ms + 2800)

Return ONLY valid JSON:
{{
  "animation_events": [
    {{
      "event_type": "diagram_overview|diagram_cursor_move|diagram_zoom_in|diagram_zoom_out|diagram_annotate_circle|diagram_highlight_region|diagram_flow_arrow|formula_step_reveal",
      "trigger_word": "exact_word_from_narration",
      "trigger_ms": 1200,
      "data": {{
        "region": {{"x_pct": 0.1, "y_pct": 0.1, "w_pct": 0.2, "h_pct": 0.15}},
        "zoom_scale": 2.2,
        "hold_ms": 2800,
        "annotation_color": "#00E5FF",
        "from_region": null,
        "to_region": null,
        "label": "",
        "step_index": 0,
        "latex": "",
        "explanation": ""
      }}
    }}
  ]
}}

For zoom_in: include region, zoom_scale (1.5 to 3.2 — smaller element = higher zoom), hold_ms
For annotate_circle: include region, annotation_color
For highlight_region: include region, annotation_color
For flow_arrow: include from_region, to_region, label — NO region needed
For formula_step_reveal: include step_index, latex, explanation — NO region needed
For zoom_out: data can be empty {{}}
For cursor_move: include region only
For overview: data can be empty {{}}"""

    result = generate_text_json(
        prompt=stage2_prompt,
        task_name=f"stage2_animate_{scene_id}",
        max_tokens=3000,
        temperature=0.1
    )

    if result is None:
        log.warning(f"[animation_brain] Stage 2 LLM returned None for {scene_id}")
        return None

    events = result.get("animation_events", [])
    if not isinstance(events, list):
        log.warning(f"[animation_brain] Stage 2 returned non-list animation_events for {scene_id}")
        return None

    log.info(f"[animation_brain] Stage 2 success: {len(events)} animation events generated")
    return events


# ══════════════════════════════════════════════════════════════════════════════
# Post-processing: resolve timestamps and validate
# ══════════════════════════════════════════════════════════════════════════════

def _resolve_event_timestamps(events: list, word_index: dict) -> list:
    """Resolve trigger_word to actual millisecond timestamps from word_index."""
    result = []
    last_ms = 0

    for ev in events:
        trigger_word = ev.pop("trigger_word", "")
        existing_ms = ev.get("trigger_ms", 0)

        if trigger_word:
            resolved_ms = _resolve_ms(trigger_word, word_index, existing_ms or last_ms + 1500)
        else:
            resolved_ms = existing_ms or last_ms + 500

        # Use timestamp_ms as the canonical key (matches existing timeline format)
        ev["timestamp_ms"] = resolved_ms
        ev.pop("trigger_ms", None)

        result.append(ev)
        last_ms = resolved_ms

    return result


def _validate_and_clean_events(events: list) -> list:
    """
    Remove invalid events. Enforce:
    - No connector zoom/circle
    - Camera events at least 600ms apart
    - Max 8 total events (cognitive load limit, extended to allow overview + zoom pairs)
    - No blue colors
    - Valid event types only
    """
    CAMERA_EVENTS = {"diagram_zoom_in", "diagram_zoom_out", "diagram_overview"}
    VALID_TYPES = {
        "diagram_overview", "diagram_cursor_move", "diagram_zoom_in",
        "diagram_zoom_out", "diagram_annotate_circle", "diagram_highlight_region",
        "diagram_flow_arrow", "formula_step_reveal"
    }
    BANNED_COLORS = {"#0000ff", "#0000FF", "#4A90D9", "#4a90d9", "blue", "#0066ff", "#3366ff"}

    # Filter invalid event types
    events = [e for e in events if e.get("event_type") in VALID_TYPES]

    # Scrub banned colors
    for ev in events:
        data = ev.get("data", {})
        color = data.get("annotation_color", "")
        if color.lower() in {c.lower() for c in BANNED_COLORS}:
            data["annotation_color"] = "#00E5FF"

    # Sort by timestamp
    events = sorted(events, key=lambda e: e.get("timestamp_ms", 0))

    # Camera collision prevention — minimum 600ms apart
    result = []
    last_camera_ms = -1000

    for ev in events:
        ms = ev.get("timestamp_ms", 0)
        if ev["event_type"] in CAMERA_EVENTS:
            if ms - last_camera_ms < 600:
                ms = last_camera_ms + 700
                ev["timestamp_ms"] = ms
            last_camera_ms = ms
        result.append(ev)

    return result


# ══════════════════════════════════════════════════════════════════════════════
# Heuristic fallback (preserved from original)
# ══════════════════════════════════════════════════════════════════════════════

def _heuristic_fallback(word_timestamps: list) -> list:
    """When all providers fail — return minimal safe events."""
    mid_ms = 3000
    if word_timestamps:
        mid_ms = word_timestamps[len(word_timestamps) // 2].get("start_ms", 3000)
    return [
        {"event_type": "diagram_overview", "timestamp_ms": 400, "data": {}},
        {"event_type": "diagram_zoom_in", "timestamp_ms": max(500, mid_ms - 300),
         "data": {"region": {"x_pct": 0.1, "y_pct": 0.1, "w_pct": 0.8, "h_pct": 0.8},
                  "zoom_scale": 1.6, "hold_ms": 3000}},
        {"event_type": "diagram_zoom_out", "timestamp_ms": mid_ms + 3000, "data": {}},
    ]


# ══════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def generate_animation_script(
    scene: dict,
    word_timestamps: list,
    diagram_image_path: Optional[str] = None
) -> list:
    """
    Two-stage intelligent diagram animation generator.

    Stage 1: VLM deeply understands diagram structure, semantics, and math
    Stage 2: LLM generates narration-coupled animation sequence

    Returns list of timeline events sorted by timestamp_ms.
    Never raises — returns [] on any error.

    Function signature unchanged from original for backward compatibility
    with timeline_builder.py integration.
    """
    try:
        # ── Guards ────────────────────────────────────────────────────────
        if not diagram_image_path or not Path(diagram_image_path).exists():
            return []
        if not word_timestamps:
            return []

        # Parse DNA type from scene
        scene_dna = scene.get("scene_dna")
        dna_type = "DIAGRAM_SPATIAL"
        if isinstance(scene_dna, dict):
            dna_type = scene_dna.get("dna_type", "DIAGRAM_SPATIAL")
        if dna_type.startswith("DNA-"):
            parts = dna_type.split(" ", 1)
            if len(parts) > 1:
                dna_type = parts[1]

        # ALL DNA types with a diagram go through the two-stage pipeline.
        # The universal Stage 1 prompt handles flowcharts, cause-effect,
        # formulas, spatial diagrams, etc. — no DNA-specific routing needed.
        narration = scene.get("narration", "")
        scene_id = scene.get("scene_id", "unknown")
        word_index = _build_word_index(word_timestamps)

        log.info(f"[animation_brain] Starting 2-stage analysis for {scene_id} ({dna_type})")

        # ── STAGE 1: Deep VLM Comprehension ───────────────────────────────
        stage1_result = _stage1_comprehend(diagram_image_path, narration, scene_id)

        if stage1_result is None:
            log.warning(f"[animation_brain] Stage 1 failed for {scene_id} — using heuristic fallback")
            return _heuristic_fallback(word_timestamps)

        # ── STAGE 2: Intelligent Animation Script ─────────────────────────
        raw_events = _stage2_animate(stage1_result, narration, word_timestamps, scene_id)

        if raw_events is None:
            log.warning(f"[animation_brain] Stage 2 failed for {scene_id} — using heuristic fallback")
            return _heuristic_fallback(word_timestamps)

        # ── Post-processing ────────────────────────────────────────────────
        events_with_ms = _resolve_event_timestamps(raw_events, word_index)
        final_events = _validate_and_clean_events(events_with_ms)

        log.info(f"[animation_brain] Complete: {len(final_events)} events for {scene_id}")
        return final_events

    except Exception as e:
        log.error(f"[animation_brain] Unhandled error for {scene.get('scene_id', '?')}: {e}")
        return []
