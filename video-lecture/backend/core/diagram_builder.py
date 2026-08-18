# -*- coding: utf-8 -*-
"""
SmartStudyInstructor — Diagram Builder (Leadde-style)
Builds clean educational SVG diagrams from scratch using LLM output and narration.
Programmatic layout engine ensures zero node overlaps or merging with guaranteed padding.
"""

import logging
import math
import re
from typing import Dict, List, Optional

from core.ai_providers import generate_text_json, generate_text_json_premium


log = logging.getLogger("diagram_builder")

COLOR_MAP = {
    "blue":   {"fill": "#E6F1FB", "stroke": "#185FA5", "text": "#0C447C"},
    "amber":  {"fill": "#FAEEDA", "stroke": "#BA7517", "text": "#633806"},
    "green":  {"fill": "#EAF3DE", "stroke": "#3B6D11", "text": "#27500A"},
    "red":    {"fill": "#FCEBEB", "stroke": "#A32D2D", "text": "#791F1F"},
    "grey":   {"fill": "#F1EFE8", "stroke": "#5F5E5A", "text": "#2C2C2A"},
    "navy":   {"fill": "#1a2744", "stroke": "#4A90D9", "text": "#ffffff"},
    "purple": {"fill": "#F0E6F6", "stroke": "#7B2D8E", "text": "#5A1A6E"},
    "teal":   {"fill": "#E0F5F5", "stroke": "#1A8A8A", "text": "#0D5C5C"},
}

# Spacing constants — guaranteed readable, spacious layout
CANVAS_W = 1280
CANVAS_H = 720
NODE_MIN_W = 135
NODE_MIN_H = 54
NODE_PADDING_X = 80    # horizontal gap between nodes
NODE_PADDING_Y = 70    # vertical gap between nodes  
MARGIN_X = 50
MARGIN_Y = 50
MAX_NODES_PER_ROW = 5  # max 5 per row for complex diagrams
MAX_ELEMENTS = 24      # allow up to 24 elements for 100% full PDF diagram coverage
                       # (raised from 16 — dense PDFs were losing nodes at the cap)



def _layout_left_to_right(elements: list) -> list:
    """
    Arrange elements in a horizontal row with proper spacing.
    If more than MAX_NODES_PER_ROW, wrap to second row.
    """
    n = len(elements)
    if not n:
        return elements
    rows = []
    
    # Split into rows of max MAX_NODES_PER_ROW
    for i in range(0, n, MAX_NODES_PER_ROW):
        rows.append(elements[i:i + MAX_NODES_PER_ROW])
    
    total_rows = len(rows)
    
    for row_idx, row in enumerate(rows):
        row_count = len(row)
        
        # Calculate total width needed for this row
        total_node_w = row_count * NODE_MIN_W
        total_gap_w = (row_count - 1) * NODE_PADDING_X
        total_row_w = total_node_w + total_gap_w
        
        # Center the row horizontally
        start_x = (CANVAS_W - total_row_w) / 2
        
        # Calculate y position for this row
        total_height = total_rows * NODE_MIN_H + (total_rows - 1) * NODE_PADDING_Y
        start_y = MARGIN_Y + (CANVAS_H - 2 * MARGIN_Y - total_height) / 2 + row_idx * (NODE_MIN_H + NODE_PADDING_Y)
        
        for col_idx, el in enumerate(row):
            el["x_px"] = start_x + col_idx * (NODE_MIN_W + NODE_PADDING_X)
            el["y_px"] = start_y
            el["w_px"] = NODE_MIN_W
            el["h_px"] = NODE_MIN_H
    
    # Convert to percentage
    for el in elements:
        el["x_pct"] = el["x_px"] / CANVAS_W
        el["y_pct"] = el["y_px"] / CANVAS_H
        el["w_pct"] = el["w_px"] / CANVAS_W
        el["h_pct"] = el["h_px"] / CANVAS_H
    
    return elements


def _layout_top_to_bottom(elements: list) -> list:
    """
    Arrange elements in vertical tiers. Elements at same level side by side.
    """
    if not elements:
        return elements
    levels = {}
    for el in elements:
        level = el.get("appear_order", 1)
        if level not in levels:
            levels[level] = []
        levels[level].append(el)
    
    total_levels = len(levels)
    level_height = (CANVAS_H - 2 * MARGIN_Y) / max(total_levels, 1)
    
    for level_idx, (level_num, level_els) in enumerate(sorted(levels.items())):
        count = len(level_els)
        total_w = count * NODE_MIN_W + (count - 1) * NODE_PADDING_X
        start_x = (CANVAS_W - total_w) / 2
        y = MARGIN_Y + level_idx * level_height + (level_height - NODE_MIN_H) / 2
        
        for col_idx, el in enumerate(level_els):
            el["x_px"] = start_x + col_idx * (NODE_MIN_W + NODE_PADDING_X)
            el["y_px"] = y
            el["w_px"] = NODE_MIN_W
            el["h_px"] = NODE_MIN_H
    
    for el in elements:
        el["x_pct"] = el.get("x_px", 0) / CANVAS_W
        el["y_pct"] = el.get("y_px", 0) / CANVAS_H
        el["w_pct"] = el.get("w_px", NODE_MIN_W) / CANVAS_W
        el["h_pct"] = el.get("h_px", NODE_MIN_H) / CANVAS_H
    
    return elements


def _layout_radial(elements: list) -> list:
    """
    One center node, rest arranged in a circle around it.
    Guaranteed minimum distance between all nodes.
    """
    if not elements:
        return elements
    
    # Center node is the first element (appear_order=1)
    center = elements[0]
    periphery = elements[1:]
    
    cx = CANVAS_W / 2
    cy = CANVAS_H / 2
    
    center["x_px"] = cx - (NODE_MIN_W + 20) / 2
    center["y_px"] = cy - (NODE_MIN_H + 10) / 2
    center["w_px"] = NODE_MIN_W + 20  # Center node slightly bigger
    center["h_px"] = NODE_MIN_H + 10
    
    if periphery:
        n_periph = len(periphery)
        min_radius = (NODE_MIN_W + NODE_PADDING_X) / (2 * math.sin(math.pi / max(n_periph, 1)))
        radius = max(min_radius, 180)
        max_radius = min(cx - MARGIN_X - NODE_MIN_W, cy - MARGIN_Y - NODE_MIN_H)
        radius = min(radius, max_radius)
        
        for i, el in enumerate(periphery):
            angle = (2 * math.pi * i / n_periph) - math.pi / 2
            px = cx + radius * math.cos(angle) - NODE_MIN_W / 2
            py = cy + radius * math.sin(angle) - NODE_MIN_H / 2
            px = max(MARGIN_X, min(px, CANVAS_W - MARGIN_X - NODE_MIN_W))
            py = max(MARGIN_Y, min(py, CANVAS_H - MARGIN_Y - NODE_MIN_H))
            el["x_px"] = px
            el["y_px"] = py
            el["w_px"] = NODE_MIN_W
            el["h_px"] = NODE_MIN_H
    
    for el in elements:
        el["x_pct"] = el.get("x_px", 0) / CANVAS_W
        el["y_pct"] = el.get("y_px", 0) / CANVAS_H
        el["w_pct"] = el.get("w_px", NODE_MIN_W) / CANVAS_W
        el["h_pct"] = el.get("h_px", NODE_MIN_H) / CANVAS_H
    
    return elements


def _layout_grid(elements: list) -> list:
    """
    Optimal grid layout for complex graphs with many nodes.
    Automatically determines best rows × cols arrangement.
    """
    if not elements:
        return elements
    n = len(elements)
    
    # Find optimal grid dimensions
    cols = math.ceil(math.sqrt(n * (CANVAS_W / CANVAS_H)))
    cols = max(2, min(cols, MAX_NODES_PER_ROW + 1))  # 2 to 5 columns
    rows = math.ceil(n / cols)
    
    usable_w = CANVAS_W - 2 * MARGIN_X
    usable_h = CANVAS_H - 2 * MARGIN_Y
    cell_w = usable_w / cols
    cell_h = usable_h / rows
    
    for idx, el in enumerate(elements):
        row = idx // cols
        col = idx % cols
        # Center node within its grid cell
        el["x_px"] = MARGIN_X + col * cell_w + (cell_w - NODE_MIN_W) / 2
        el["y_px"] = MARGIN_Y + row * cell_h + (cell_h - NODE_MIN_H) / 2
        el["w_px"] = NODE_MIN_W
        el["h_px"] = NODE_MIN_H
    
    for el in elements:
        el["x_pct"] = el.get("x_px", 0) / CANVAS_W
        el["y_pct"] = el.get("y_px", 0) / CANVAS_H
        el["w_pct"] = el.get("w_px", NODE_MIN_W) / CANVAS_W
        el["h_pct"] = el.get("h_px", NODE_MIN_H) / CANVAS_H
    
    return elements


def _get_connection_endpoints(from_el: dict, to_el: dict) -> tuple:
    """
    Calculate start/end points at node BORDERS, not centers.
    Adds 4px clearance from edge.
    """
    # Centers in pixels
    fx = (from_el["x_pct"] + from_el["w_pct"] / 2) * CANVAS_W
    fy = (from_el["y_pct"] + from_el["h_pct"] / 2) * CANVAS_H
    tx = (to_el["x_pct"] + to_el["w_pct"] / 2) * CANVAS_W
    ty = (to_el["y_pct"] + to_el["h_pct"] / 2) * CANVAS_H

    dx = tx - fx
    dy = ty - fy
    dist = max((dx**2 + dy**2) ** 0.5, 1.0)
    ux, uy = dx / dist, dy / dist  # unit vector

    # From node half-dimensions + 4px clearance
    fw = from_el["w_pct"] * CANVAS_W / 2 + 4
    fh = from_el["h_pct"] * CANVAS_H / 2 + 4
    t_from = min(
        fw / max(abs(ux), 0.001),
        fh / max(abs(uy), 0.001)
    )
    sx = fx + ux * t_from
    sy = fy + uy * t_from

    # To node half-dimensions + 4px clearance
    tw2 = to_el["w_pct"] * CANVAS_W / 2 + 4
    th2 = to_el["h_pct"] * CANVAS_H / 2 + 4
    t_to = min(
        tw2 / max(abs(ux), 0.001),
        th2 / max(abs(uy), 0.001)
    )
    ex = tx - ux * t_to
    ey = ty - uy * t_to

    return sx, sy, ex, ey


def _get_edge_point(from_el: dict, to_el: dict, canvas_w: int = CANVAS_W, canvas_h: int = CANVAS_H) -> tuple:
    return _get_connection_endpoints(from_el, to_el)


def _resolve_node_collisions(elements: list, min_dist: float = 130.0, iterations: int = 60) -> list:
    """
    Guarantees zero overlapping nodes using a mathematical relaxation pass.
    Adjusts x_px and y_px if distance between any two node centers < min_dist.
    Clamps all nodes within canvas margins.
    """
    if not elements or len(elements) < 2:
        return elements

    for _ in range(iterations):
        collision_found = False
        for i in range(len(elements)):
            for j in range(i + 1, len(elements)):
                e1 = elements[i]
                e2 = elements[j]
                
                w1 = e1.get("w_px", NODE_MIN_W)
                h1 = e1.get("h_px", NODE_MIN_H)
                w2 = e2.get("w_px", NODE_MIN_W)
                h2 = e2.get("h_px", NODE_MIN_H)

                c1x = e1.get("x_px", 0) + w1 / 2.0
                c1y = e1.get("y_px", 0) + h1 / 2.0
                c2x = e2.get("x_px", 0) + w2 / 2.0
                c2y = e2.get("y_px", 0) + h2 / 2.0

                dx = c2x - c1x
                dy = c2y - c1y
                dist = math.hypot(dx, dy)

                req_dist = max(min_dist, (w1 + w2) / 2.0 + 30.0)

                if dist < req_dist:
                    collision_found = True
                    overlap = req_dist - (dist if dist > 0.001 else 0.001)
                    nx = (dx / dist) if dist > 0.001 else 1.0
                    ny = (dy / dist) if dist > 0.001 else 0.0

                    shift_x = nx * (overlap / 2.0)
                    shift_y = ny * (overlap / 2.0)

                    e1["x_px"] -= shift_x
                    e1["y_px"] -= shift_y
                    e2["x_px"] += shift_x
                    e2["y_px"] += shift_y

                    # Clamp to canvas margins
                    e1["x_px"] = max(MARGIN_X, min(e1["x_px"], CANVAS_W - MARGIN_X - w1))
                    e1["y_px"] = max(MARGIN_Y, min(e1["y_px"], CANVAS_H - MARGIN_Y - h1))
                    e2["x_px"] = max(MARGIN_X, min(e2["x_px"], CANVAS_W - MARGIN_X - w2))
                    e2["y_px"] = max(MARGIN_Y, min(e2["y_px"], CANVAS_H - MARGIN_Y - h2))

        if not collision_found:
            break

    # Re-update percentages
    for el in elements:
        w = el.get("w_px", NODE_MIN_W)
        h = el.get("h_px", NODE_MIN_H)
        el["x_pct"] = el["x_px"] / CANVAS_W
        el["y_pct"] = el["y_px"] / CANVAS_H
        el["w_pct"] = w / CANVAS_W
        el["h_pct"] = h / CANVAS_H

    return elements


def _filter_to_vlm_confirmed(
    elements: list,
    connections: list,
    vlm_regions: list,
    vlm_connectors: list,
) -> tuple:
    """
    FIX 3 (diagram fidelity): drop any node/edge the LLM invented that the VLM
    did NOT actually see in the PDF image. Only elements whose label/id matches
    a VLM-confirmed region survive. If the VLM produced no regions (e.g. VLM
    unavailable), we keep everything (no ground-truth to filter against).
    Returns (filtered_elements, filtered_connections).
    """
    if not vlm_regions:
        return elements, connections

    def _norm(s: str) -> str:
        return re.sub(r"[^a-z0-9]", "", str(s or "").lower())

    # Build the set of VLM-confirmed labels/ids (character-normalized)
    confirmed = set()
    for r in vlm_regions:
        if not isinstance(r, dict):
            continue
        for key in ("label", "region_id", "id"):
            v = _norm(r.get(key, ""))
            if v:
                confirmed.add(v)

    def _is_confirmed(el: dict) -> bool:
        text = _norm(el.get("text", ""))
        eid = _norm(el.get("id", ""))
        for c in confirmed:
            # match if VLM label is contained in node text or vice-versa
            if text and (text == c or text in c or c in text):
                return True
            if eid and (eid == c or eid in c or c in eid):
                return True
        return False

    kept = [el for el in elements if _is_confirmed(el)]
    dropped = len(elements) - len(kept)

    # Safety: never let the fidelity filter destroy a diagram. If it would drop
    # a large fraction of nodes (>40%), the label-match heuristic is unreliable
    # for THIS diagram (e.g. narration-derived step/helper nodes the VLM never
    # labelled) — keep originals so real steps/helpers survive. We only trust
    # the filter to remove a few clearly-invented extras.
    if len(elements) > 0 and len(kept) < 0.6 * len(elements):
        log.info(
            f"[diagram_builder] VLM-fidelity filter would drop "
            f"{len(elements) - len(kept)}/{len(elements)} nodes (>40%); "
            f"keeping originals — likely narrated step/helper nodes, not junk."
        )
        return elements, connections
    if len(kept) < 2:

        log.warning(
            f"[diagram_builder] VLM-fidelity filter matched <2 nodes "
            f"({len(kept)}/{len(elements)}); keeping originals to avoid empty diagram."
        )
        return elements, connections

    if dropped:
        log.info(f"[diagram_builder] VLM-fidelity filter dropped {dropped} invented node(s).")

    kept_ids = {el.get("id") for el in kept}
    kept_conns = [
        c for c in connections
        if c.get("from_id") in kept_ids and c.get("to_id") in kept_ids
    ]
    return kept, kept_conns


def assign_layout_coordinates(elements: list, layout_preset: str):

    """
    Automatically dispatches layout mode to calculate clean coordinates,
    then runs a mathematical collision relaxation pass to guarantee zero overlaps.
    """
    if layout_preset == "radial":
        elements = _layout_radial(elements)
    elif layout_preset == "top_to_bottom":
        elements = _layout_top_to_bottom(elements)
    elif layout_preset == "grid":
        elements = _layout_grid(elements)
    else:
        # Auto-select: use grid for 6+ elements, left_to_right for fewer
        if len(elements) >= 6:
            elements = _layout_grid(elements)
        else:
            elements = _layout_left_to_right(elements)

    return _resolve_node_collisions(elements)



def _build_svg(diagram_data: dict) -> str:
    """Build complete SVG with per-connection colors, title, sublabels inside nodes, and weight badges."""
    elements = diagram_data.get("elements", [])
    connections = diagram_data.get("connections", [])
    title = diagram_data.get("title", "")
    
    el_map = {e["id"]: e for e in elements if "id" in e}
    
    # Collect unique connection colors for arrowhead markers
    conn_colors_used = set()
    for conn in connections:
        c = conn.get("color", "amber")
        conn_colors_used.add(c)
    
    # Build <defs> with per-color arrowhead markers
    defs_parts = []
    for color_key in conn_colors_used:
        colors = COLOR_MAP.get(color_key, COLOR_MAP["amber"])
        stroke_color = colors["stroke"]
        marker_id = f"arr_{color_key}"
        defs_parts.append(
            f'<marker id="{marker_id}" viewBox="0 0 10 10" refX="8" refY="5" '
            f'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
            f'<path d="M2 1L8 5L2 9" fill="none" stroke="{stroke_color}" stroke-width="1.5" '
            f'stroke-linecap="round"/></marker>'
        )
    # Default amber marker fallback
    defs_parts.append(
        '<marker id="arr" viewBox="0 0 10 10" refX="8" refY="5" '
        'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
        '<path d="M2 1L8 5L2 9" fill="none" stroke="#BA7517" stroke-width="1.5" '
        'stroke-linecap="round"/></marker>'
    )
    
    svg_parts = [
        f'<svg id="prog-diagram" viewBox="0 0 {CANVAS_W} {CANVAS_H}" '
        f'preserveAspectRatio="xMidYMid meet" '
        f'xmlns="http://www.w3.org/2000/svg" '
        f'style="width:100%;height:100%;min-height:360px;">'
        f'<defs>{chr(10).join(defs_parts)}</defs>'
    ]
    
    # Diagram title at top
    if title:
        svg_parts.append(
            f'<text x="{CANVAS_W / 2}" y="28" '
            f'text-anchor="middle" font-size="16" font-weight="700" '
            f'fill="#c9b99a" letter-spacing="0.5" opacity="0.85">{title}</text>'
        )
    
    # Draw connections FIRST (behind nodes)
    for conn in connections:
        from_el = el_map.get(conn.get("from_id"))
        to_el = el_map.get(conn.get("to_id"))
        if not from_el or not to_el:
            continue
        
        sx, sy, ex, ey = _get_connection_endpoints(from_el, to_el)
        length = ((ex-sx)**2 + (ey-sy)**2)**0.5
        conn_id = f"conn_{conn.get('from_id')}_{conn.get('to_id')}"
        
        # Use per-connection color
        conn_color_key = conn.get("color", "amber")
        conn_colors = COLOR_MAP.get(conn_color_key, COLOR_MAP["amber"])
        conn_stroke = conn_colors["stroke"]
        marker_ref = f"url(#arr_{conn_color_key})" if conn_color_key in conn_colors_used else "url(#arr)"
        
        # Directed vs undirected
        is_directed = conn.get("directed", True)
        marker_attr = f'marker-end="{marker_ref}"' if is_directed else ''
        
        # Dashed style support
        style = conn.get("style", "solid")
        dash_attr = 'stroke-dasharray="8 4"' if style == "dashed" else f'stroke-dasharray="{length:.1f}" stroke-dashoffset="{length:.1f}"'
        
        svg_parts.append(
            f'<line id="{conn_id}" '
            f'x1="{sx:.1f}" y1="{sy:.1f}" x2="{ex:.1f}" y2="{ey:.1f}" '
            f'stroke="{conn_stroke}" stroke-width="2" '
            f'{dash_attr} '
            f'{marker_attr} opacity="0" fill="none"/>'
        )
        
        # Connection label (above the line)
        if conn.get("label"):
            mx = (sx + ex) / 2
            my = (sy + ey) / 2 - 12
            svg_parts.append(
                f'<text x="{mx:.1f}" y="{my:.1f}" '
                f'text-anchor="middle" font-size="11" font-weight="500" '
                f'fill="{conn_stroke}" '
                f'opacity="0" id="{conn_id}_label">{conn["label"]}</text>'
            )
        
        # Edge weight rendering with prominent background pill
        weight = conn.get("weight", "")
        if weight:
            wmx = (sx + ex) / 2
            wmy = (sy + ey) / 2 + 10
            weight_str = str(weight)
            pill_w = max(36, len(weight_str) * 9 + 16)  # dynamic width based on text length
            svg_parts.append(
                f'<rect x="{wmx - pill_w/2:.1f}" y="{wmy - 10:.1f}" '
                f'width="{pill_w}" height="20" rx="6" '
                f'fill="#1a2744" stroke="{conn_stroke}" stroke-width="1" '
                f'opacity="0" id="{conn_id}_wbg"/>'
            )
            svg_parts.append(
                f'<text x="{wmx:.1f}" y="{wmy + 4:.1f}" '
                f'text-anchor="middle" font-size="11" font-weight="700" '
                f'fill="#ffffff" opacity="0" id="{conn_id}_wlbl">{weight_str}</text>'
            )
    
    # Draw nodes
    for el in elements:
        eid = el.get("id")
        if not eid:
            continue
        x = el.get("x_pct", 0) * CANVAS_W
        y = el.get("y_pct", 0) * CANVAS_H
        w = el.get("w_pct", 0) * CANVAS_W
        h = el.get("h_pct", 0) * CANVAS_H
        cx = x + w / 2
        cy = y + h / 2
        
        colors = COLOR_MAP.get(el.get("color", "blue"), COLOR_MAP["blue"])
        shape = el.get("shape", "rounded_rect")
        text = el.get("text", "")
        sublabel = el.get("sublabel", "")
        
        svg_parts.append(f'<g id="{eid}" opacity="0">')
        
        if shape == "circle":
            r = min(w, h) / 2
            svg_parts.append(
                f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" '
                f'fill="{colors["fill"]}" stroke="{colors["stroke"]}" stroke-width="2"/>'
            )
        elif shape == "diamond":
            pts = f"{cx:.1f},{y:.1f} {x+w:.1f},{cy:.1f} {cx:.1f},{y+h:.1f} {x:.1f},{cy:.1f}"
            svg_parts.append(
                f'<polygon points="{pts}" '
                f'fill="{colors["fill"]}" stroke="{colors["stroke"]}" stroke-width="2"/>'
            )
        else:  # rect or rounded_rect
            rx_val = "10" if shape == "rounded_rect" else "0"
            svg_parts.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
                f'rx="{rx_val}" fill="{colors["fill"]}" stroke="{colors["stroke"]}" '
                f'stroke-width="2"/>'
            )
        
        # Text rendering — main label + optional sublabel INSIDE the node
        if sublabel:
            # Two-line layout: main text + sublabel inside node
            svg_parts.append(
                f'<text x="{cx:.1f}" y="{cy - 7:.1f}" '
                f'text-anchor="middle" dominant-baseline="central" '
                f'font-size="12" font-weight="700" fill="{colors["text"]}">{text}</text>'
            )
            svg_parts.append(
                f'<text x="{cx:.1f}" y="{cy + 10:.1f}" id="{eid}_sublabel" '
                f'text-anchor="middle" dominant-baseline="central" '
                f'font-size="10" font-weight="500" fill="{colors["text"]}" opacity="0.7">{sublabel}</text>'
            )
        else:
            # Single text — smart multi-line split
            words = text.split()
            if len(words) <= 3:
                svg_parts.append(
                    f'<text x="{cx:.1f}" y="{cy:.1f}" '
                    f'text-anchor="middle" dominant-baseline="central" '
                    f'font-size="12" font-weight="700" fill="{colors["text"]}">{text}</text>'
                )
            else:
                line1 = " ".join(words[:len(words)//2])
                line2 = " ".join(words[len(words)//2:])
                svg_parts.append(
                    f'<text x="{cx:.1f}" y="{cy-8:.1f}" '
                    f'text-anchor="middle" dominant-baseline="central" '
                    f'font-size="11" font-weight="700" fill="{colors["text"]}">{line1}</text>'
                )
                svg_parts.append(
                    f'<text x="{cx:.1f}" y="{cy+8:.1f}" '
                    f'text-anchor="middle" dominant-baseline="central" '
                    f'font-size="11" font-weight="500" fill="{colors["text"]}">{line2}</text>'
                )
        
        svg_parts.append('</g>')
    
    # Floating computation overlay container (used by prog_compute_step events)
    svg_parts.append(
        f'<g id="prog-compute-overlay" opacity="0">'
        f'<rect id="prog-compute-bg" x="{CANVAS_W - 320}" y="{CANVAS_H - 55}" '
        f'width="300" height="40" rx="8" fill="#0d1b2a" stroke="#4A90D9" stroke-width="1" opacity="0.92"/>'
        f'<text id="prog-compute-text" x="{CANVAS_W - 170}" y="{CANVAS_H - 30}" '
        f'text-anchor="middle" dominant-baseline="central" '
        f'font-size="12" font-weight="600" fill="#00E5FF"></text>'
        f'</g>'
    )
    
    svg_parts.append('</svg>')
    return "\n".join(svg_parts)


def _validate_diagram_schema(
    data: dict, 
    expected_vlm_regions: list = None,
    expected_vlm_connectors: list = None
) -> tuple[bool, list[str]]:
    """Strictly validate that diagram specification contains valid nodes, connections, numeric/label values, and VLM completeness."""
    errors = []
    if not isinstance(data, dict):
        return False, ["Diagram payload is not a JSON object"]
    
    elements = data.get("elements")
    if not isinstance(elements, list) or len(elements) < 2:
        errors.append(f"elements must be a list containing at least 2 nodes (got {len(elements) if isinstance(elements, list) else 'non-list'})")
        return False, errors

    element_ids = set()
    element_texts_lower = set()
    for idx, el in enumerate(elements):
        if not isinstance(el, dict):
            errors.append(f"Element index {idx} is not a valid JSON object")
            continue
        eid = str(el.get("id", "")).strip()
        text = str(el.get("text", "")).strip()
        if not eid:
            errors.append(f"Element index {idx} missing required 'id'")
        else:
            element_ids.add(eid)
        if not text:
            errors.append(f"Element '{eid}' missing required 'text' label")
        else:
            element_texts_lower.add(text.lower())
            if text.lower() in ["placeholder", "stub", "tbd", "undefined", "null", "none"]:
                errors.append(f"Element '{eid}' contains invalid placeholder label '{text}'")

    # Check VLM node completeness: ensure no node detected by Qwen VLM was dropped!
    if expected_vlm_regions:
        for r in expected_vlm_regions:
            lbl = str(r.get("label", r.get("region_id", ""))).strip()
            if lbl and lbl.lower() not in element_texts_lower and lbl.lower() not in element_ids:
                matched = any(lbl.lower() in t or t in lbl.lower() for t in element_texts_lower)
                if not matched:
                    errors.append(f"Missing required node from PDF: '{lbl}'. You MUST include all nodes detected in the PDF image!")

    connections = data.get("connections", [])
    if not isinstance(connections, list):
        errors.append("connections field must be a list")
    else:
        for idx, conn in enumerate(connections):
            if not isinstance(conn, dict):
                errors.append(f"Connection index {idx} is not an object")
                continue
            f_id = str(conn.get("from_id", "")).strip()
            t_id = str(conn.get("to_id", "")).strip()
            if not f_id or f_id not in element_ids:
                errors.append(f"Connection index {idx} 'from_id' ('{f_id}') does not exist in elements IDs: {list(element_ids)}")
            if not t_id or t_id not in element_ids:
                errors.append(f"Connection index {idx} 'to_id' ('{t_id}') does not exist in elements IDs: {list(element_ids)}")

    # Check connection count completeness
    if expected_vlm_connectors and len(expected_vlm_connectors) > len(connections) + 1:
        errors.append(f"Incomplete connections: PDF image contains {len(expected_vlm_connectors)} connections, but generated diagram only has {len(connections)}. Do not skip connections!")

    return (len(errors) == 0), errors


# ══════════════════════════════════════════════════════════════════════════
# UPGRADE 2 — THREE-CALL DIAGRAM GENERATION (anti-truncation)
# Split diagram generation into three small LLM calls so a response is never
# truncated. Each call requests a small amount of data with a tight token cap.
# ══════════════════════════════════════════════════════════════════════════

def _call_nodes(scene: dict, narration: str, vlm_node_context: str) -> list:
    """
    CALL 1 — request ONLY the nodes list (up to MAX_ELEMENTS nodes) with placement
    coordinates on the canvas. A generous token cap lets the model emit EVERY node
    the PDF diagram contains, so dense diagrams are drawn completely and never
    truncated at the source. Returns a list of element dicts (may be empty on failure).
    """
    prompt = f"""You are an educational diagram architect. Return ONLY the NODES for this diagram.

TEACHER'S NARRATION (trigger_keyword must be an EXACT word from this text):
{narration[:2000]}

DIAGRAM CONTEXT:
{vlm_node_context}
Diagram type hint: {scene.get('diagram_type', 'unknown')}

CANVAS: {CANVAS_W} x {CANVAS_H} pixels. Place nodes with explicit x,y centers.
Keep at least 130px between any two node centers. Spread nodes across up to
{MAX_NODES_PER_ROW} per row and stack multiple rows so nothing overlaps.

RULES (include EVERY node the diagram needs — up to {MAX_ELEMENTS} nodes; do NOT drop any):

WHAT TO INCLUDE (be complete — do NOT under-draw):
1. Every REAL node from the PDF diagram and its connections, using the EXACT
   labels/weights shown in the PDF (Node A, B, C... with their arrows/edges).
2. EVERY computation/process STEP the narration walks through — if the teacher
   explains a sequence (e.g. "first visit A, then relax edge A→B, then pick C"),
   each step must be a node/sublabel so the viewer sees the full progression.
3. Helper elements that AID understanding when the narration references them:
   distance labels (d=0), current-node markers, cost/weight pills, highlights.

WHAT TO EXCLUDE (keep it clean):
- Do NOT invent decorative shapes, filler boxes, unrelated examples, or nodes
  that neither appear in the PDF nor are spoken about in the narration.
- Every element must map to either a real PDF node/edge OR a step/helper the
  narration actually mentions. If it's not in the PDF and not narrated, drop it.

- shape: "circle" = graph nodes / atoms / people; "rounded_rect" = process steps / modules; "diamond" = decision points
- color meaning: blue=primary concept, green=output/result, amber=process/active step, red=deletion/error, grey=neutral, purple=special path, teal=secondary
- trigger_keyword: the EXACT word from the narration spoken when this element is introduced
- initial: "animated" = appears during narration at its trigger word; "visible" = present from the start
- sublabel: optional computed value like "d=0" or "cost=5" (empty string if none)


Return ONLY valid JSON, nothing else:
{{
  "elements": [
    {{"id": "e1", "type": "node", "text": "exact label", "sublabel": "", "color": "blue", "shape": "circle", "x": 120, "y": 260, "trigger_keyword": "word", "appear_order": 1, "initial": "animated"}}
  ]
}}"""
    try:
        # Generous cap: up to MAX_ELEMENTS fully-specified nodes need room so the
        # JSON is never cut off mid-array (each node ~90 tokens → ~2200 for 24).
        data = generate_text_json(prompt, "diagram_nodes", max_tokens=4000, temperature=0.1)

        if isinstance(data, dict):
            els = data.get("elements", [])
            if isinstance(els, list):
                return els[:MAX_ELEMENTS]

    except Exception as _e:
        import logging
        logging.getLogger("diagram_builder").warning(f"[diagram_builder] _call_nodes failed: {_e}")
    return []


def _call_edges(scene: dict, narration: str, elements: list) -> list:
    """
    CALL 2 — request ONLY the edges list between the CONFIRMED nodes from call 1.
    Tight 800-token cap. Returns a list of connection dicts (may be empty).
    """
    node_lines = "\n".join(
        f"- id={e.get('id')} label=\"{e.get('text','')}\""
        for e in elements if isinstance(e, dict)
    )
    prompt = f"""You are an educational diagram architect. Return ONLY the EDGES connecting these confirmed nodes.

CONFIRMED NODES (use these exact ids in from_id / to_id):
{node_lines}

TEACHER'S NARRATION (trigger_keyword must be an EXACT word from this text):
{narration[:1500]}

RULES:
- weight: the numeric weight/distance/cost shown on the edge in the PDF (empty string if none)
- directed: true for arrows, false for undirected edges
- highlighted: true if this edge is part of a highlighted/shortest path
- trigger_keyword: the EXACT narration word spoken when this edge is drawn
- color: amber=process flow, blue=data flow, red=rejection, purple=highlighted path

Return ONLY valid JSON, nothing else:
{{
  "connections": [
    {{"from_id": "e1", "to_id": "e2", "label": "", "weight": "5", "directed": true, "highlighted": false, "color": "amber", "style": "solid", "trigger_keyword": "word"}}
  ]
}}"""
    try:
        data = generate_text_json(prompt, "diagram_edges", max_tokens=2000, temperature=0.1)
        if isinstance(data, dict):
            conns = data.get("connections", [])
            if isinstance(conns, list):
                return conns
    except Exception as _e:
        import logging
        logging.getLogger("diagram_builder").warning(f"[diagram_builder] _call_edges failed: {_e}")
    return []


def _call_deletions(scene: dict, narration: str, elements: list) -> list:
    """
    CALL 3 — request ONLY the ids of nodes that get deleted during the
    explanation, plus each deletion's trigger_keyword. Called ONLY when
    scene['has_deletions'] is true. Tight 200-token cap.
    Returns a list of {id, trigger_keyword} dicts (may be empty).
    """
    node_ids = ", ".join(str(e.get("id")) for e in elements if isinstance(e, dict))
    prompt = f"""Return ONLY the node ids that get DELETED during this explanation.

NODE IDS: {node_ids}

NARRATION (trigger_keyword must be an EXACT word from this text):
{narration[:1200]}

Return ONLY valid JSON:
{{"deletions": [{{"id": "e3", "trigger_keyword": "remove"}}]}}"""
    try:
        data = generate_text_json(prompt, "diagram_deletions", max_tokens=200, temperature=0.1)
        if isinstance(data, dict):
            dels = data.get("deletions", [])
            if isinstance(dels, list):
                return dels
    except Exception as _e:
        import logging
        logging.getLogger("diagram_builder").warning(f"[diagram_builder] _call_deletions failed: {_e}")
    return []


def generate_diagram_svg_and_events(
    scene: dict,
    word_timestamps: list
) -> dict:
    """
    Returns diagram SVG layout data and synced GSAP timeline event definitions.
    Enforces strict validation, self-correction retry, and zero stub fallbacks.

    UPGRADE 2: primary generation uses three small LLM calls (nodes → edges →
    deletions) so responses never truncate. The legacy single-large-call path
    remains as a fallback if the three-call assembly fails validation.
    """

    try:
        dna_dict = scene.get("scene_dna") or {}
        dna_type = dna_dict.get("dna_type", "")
        
        is_diagram_dna = any(
            target in dna_type
            for target in ["PROCESS_FLOW", "CAUSE_EFFECT", "DIAGRAM_SPATIAL", "WORKED_EXAMPLE"]
        )
        
        if not is_diagram_dna:
            return {"has_programmatic_diagram": False}
            
        topic = scene.get("heading_left") or scene.get("topic", "Diagram Scene")
        narration = scene.get("narration", "")
        diagram_desc = scene.get("diagram_description") or "No description available"

        # V17: Build VLM node/edge context from scene's diagram_data (populated by vlm_service)
        vlm_node_context = ""
        diagram_data_vlm = scene.get("diagram_data") or {}
        if isinstance(diagram_data_vlm, dict):
            vlm_regions = diagram_data_vlm.get("regions", []) or diagram_data_vlm.get("components", [])
            vlm_connectors = diagram_data_vlm.get("connectors", [])
            if vlm_regions:
                vlm_node_context += "\nVLM-EXTRACTED NODES FROM PDF IMAGE (use these exact labels):\n"
                for r in vlm_regions:
                    lbl = r.get("label", r.get("region_id", ""))
                    desc = r.get("description", r.get("role", ""))
                    vlm_node_context += f"- Node \"{lbl}\": {desc}\n"
            if vlm_connectors:
                vlm_node_context += "\nVLM-EXTRACTED CONNECTIONS FROM PDF IMAGE:\n"
                for c in vlm_connectors:
                    f_id = c.get("from_region_id", c.get("from", ""))
                    t_id = c.get("to_region_id", c.get("to", ""))
                    lbl = c.get("label", "")
                    wgt = c.get("weight", "")
                    vlm_node_context += f"- {f_id} → {t_id}" + (f" (weight: {wgt})" if wgt else "") + (f" label: \"{lbl}\"" if lbl else "") + "\n"

        # V18: Build computation steps context
        comp_steps_ctx = ""
        step_seq = scene.get('diagram_step_sequence', [])
        if step_seq:
            comp_steps_ctx = "\nDIAGRAM STEP-BY-STEP SEQUENCE (follow this EXACT order when assigning appear_order):\n"
            for si, st in enumerate(step_seq):
                comp_steps_ctx += f"  Step {si+1}: {st}\n"

        prompt = f"""You are a world-class educational diagram architect designing a complete, faithful diagram for a lecture video.

Your job: Reproduce the PDF's diagram EXACTLY — every node, every edge, every weight, every label. Then animate each element in sync with the teacher's narration.

IMMUTABLE RULES:
- Include ALL nodes and ALL edges from the PDF. Do NOT summarize or skip elements.
- Use the EXACT labels shown in the PDF for node text. Do NOT use generic placeholders (like "node1", "tbd", "placeholder").
- Include ALL edge weights/distances/costs if they exist in the PDF.
- Animation trigger_keywords MUST be EXACT words that appear in the narration text below.

═══════════════════════════════════════════════
TEACHER'S NARRATION (trigger_keywords must come from this text):
═══════════════════════════════════════════════
{narration[:3000]}

═══════════════════════════════════════════════
DIAGRAM CONTEXT FROM PDF ANALYSIS
═══════════════════════════════════════════════
DNA type: {dna_type}
Diagram description: {diagram_desc}
Diagram type hint: {scene.get('diagram_type', 'unknown')}
Has node insertions: {scene.get('has_insertions', False)}
Has node deletions: {scene.get('has_deletions', False)}
Has edge weights: {scene.get('has_edge_weights', False)}
{vlm_node_context}
{comp_steps_ctx}

═══════════════════════════════════════════════
CANVAS: {CANVAS_W} x {CANVAS_H} pixels
═══════════════════════════════════════════════

DESIGN RULES:

1. ELEMENT COUNT: Include ALL nodes from the PDF, up to {MAX_ELEMENTS} elements maximum. If the PDF has 8 nodes, you MUST include all 8. Do NOT artificially reduce.

2. SHAPES:
   - "circle": graph nodes, vertices, atoms, endpoints
   - "rounded_rect": process boxes, concepts, modules, stages
   - "diamond": decision points, conditionals

3. COLORS (use meaningfully):
   - "blue": primary/source nodes, main concepts
   - "green": outputs, results, destination nodes, positive
   - "amber": processes, active steps, in-progress
   - "red": errors, deletions, danger, rejected paths
   - "grey": neutral, start/end, context elements
   - "purple": special path, highlighted traversal, visited nodes
   - "teal": secondary concepts, intermediate nodes

4. ANIMATION PHASES:
   - "initial": "visible" = appears at scene start (background structure elements)
   - "initial": "animated" = appears at the EXACT moment the teacher says trigger_keyword
   - appear_order: chronological order matching the narration flow (1=first mentioned, 2=second, etc.)
   - trigger_keyword: MUST be a word that ACTUALLY EXISTS in the narration above. Search for it!

5. SUBLABELS: Use sublabel for computational values like "d=0", "cost=∞", "visited", "w=5". These appear as a second line inside the node.

6. CONNECTIONS:
   - Include EVERY edge/arrow from the PDF diagram
   - "from_id" and "to_id" MUST match the exact "id" of nodes in the elements list
   - "weight": the numeric weight/distance/cost shown on this edge (empty string if none)
   - "color": match the semantic meaning (amber=process flow, blue=data flow, red=rejection, purple=highlighted path)
   - "directed": true for arrows, false for undirected edges
   - "style": "solid" for normal, "dashed" for optional/conditional paths
   - "label": short text label on the edge (if any)

7. DELETIONS: If a node gets removed during the explanation, set "deleted_at_step" (integer) and "delete_trigger_keyword" (exact narration word)

8. COMPUTATION STEPS: If the diagram involves algorithm steps (e.g., Dijkstra, BFS, sorting), include a "computation_steps" array describing each step. Each step has a "text" (what's computed) and "trigger_keyword" (when teacher says it).

9. LAYOUT: Choose the layout that best matches the PDF:
   - "left_to_right": flowcharts, pipelines, timelines
   - "top_to_bottom": hierarchies, trees, layered architectures
   - "radial": star topology, concept maps with central node
   - "grid": complex graphs with 6+ nodes, networks

Return ONLY valid JSON:
{{
  "diagram_type": "flowchart|process_steps|cause_effect|comparison|concept_map|timeline|graph|tree|biological|circuit",
  "title": "concise diagram title (3-6 words)",
  "elements": [
    {{
      "id": "e1",
      "type": "node",
      "text": "exact label from PDF",
      "sublabel": "d=0 or cost=5 or empty string",
      "color": "blue|amber|green|red|grey|purple|teal",
      "shape": "rounded_rect|circle|diamond",
      "trigger_keyword": "exact_word_from_narration",
      "appear_order": 1,
      "initial": "visible|animated",
      "deleted_at_step": null,
      "delete_trigger_keyword": ""
    }}
  ],
  "connections": [
    {{"from_id": "e1", "to_id": "e2", "label": "", "color": "amber", "weight": "5", "directed": true, "style": "solid"}}
  ],
  "computation_steps": [
    {{"step": 1, "text": "Initialize source A with distance 0", "trigger_keyword": "initialize"}},
    {{"step": 2, "text": "Update B: d=4 via edge A→B", "trigger_keyword": "update"}}
  ],
  "layout": "left_to_right|top_to_bottom|radial|grid"
}}"""

        # Extract VLM expected nodes & connectors to enforce completeness
        exp_regions = diagram_data_vlm.get("regions", []) or diagram_data_vlm.get("components", []) if isinstance(diagram_data_vlm, dict) else []
        exp_connectors = diagram_data_vlm.get("connectors", []) if isinstance(diagram_data_vlm, dict) else []

        # ── UPGRADE 2: THREE-CALL GENERATION (PRIMARY PATH) ──────────────────
        # Each call requests a small payload so the response is never truncated.
        log.info(f"Generating diagram for '{topic}' via three-call split (nodes → edges → deletions)...")
        diagram_data = None
        try:
            nodes = _call_nodes(scene, narration, vlm_node_context)
            if nodes and len(nodes) >= 2:
                edges = _call_edges(scene, narration, nodes)  # partial diagram is fine if this fails
                deletions = []
                if scene.get("has_deletions"):
                    deletions = _call_deletions(scene, narration, nodes)
                    # Fold deletion metadata back onto the confirmed nodes
                    del_map = {str(d.get("id")): d.get("trigger_keyword", "") for d in deletions if isinstance(d, dict)}
                    for step_i, n in enumerate(nodes):
                        nid = str(n.get("id"))
                        if nid in del_map:
                            n["deleted_at_step"] = step_i + 1
                            n["delete_trigger_keyword"] = del_map[nid]
                assembled = {
                    "diagram_type": scene.get("diagram_type", "graph"),
                    "title": topic if isinstance(topic, str) else "Diagram",
                    "elements": nodes,
                    "connections": edges,
                    "computation_steps": [],
                    "layout": "grid" if len(nodes) >= 6 else "left_to_right",
                }
                ok3, errs3 = _validate_diagram_schema(
                    assembled, expected_vlm_regions=exp_regions, expected_vlm_connectors=exp_connectors
                )
                if ok3:
                    diagram_data = assembled
                    log.info(f"[diagram_builder] Three-call assembly succeeded: {len(nodes)} nodes, {len(edges)} edges, {len(deletions)} deletions")
                else:
                    log.warning(f"[diagram_builder] Three-call assembly failed validation: {errs3}. Falling back to single-call.")
        except Exception as _e3:
            log.warning(f"[diagram_builder] Three-call generation errored: {_e3}. Falling back to single-call.")

        # ── FALLBACK: legacy single large call (only if three-call did not yield a valid diagram)
        if diagram_data is None:
            log.info(f"Generating programmatic diagram for topic '{topic}' (single-call fallback)...")
            # 8192 tokens so dense diagrams (up to MAX_ELEMENTS nodes + all edges +
            # computation steps) are never truncated mid-JSON.
            diagram_data = generate_text_json(prompt, "diagram_builder", max_tokens=8192, temperature=0.1)

        # ── PRIORITY 1: SCHEMA VALIDATION & AUTOMATIC RETRY ──────────────────
        is_valid, errors = _validate_diagram_schema(diagram_data, expected_vlm_regions=exp_regions, expected_vlm_connectors=exp_connectors) if diagram_data else (False, ["No JSON returned from LLM"])

        
        if not is_valid:
            log.warning(f"[diagram_builder] Validation failed on Attempt 1 for '{topic}': {errors}. Triggering self-correction retry...")
            retry_prompt = (
                f"{prompt}\n\n"
                "CRITICAL VALIDATION ERRORS FROM YOUR PREVIOUS ATTEMPT:\n"
                + "\n".join(f"- {err}" for err in errors)
                + "\n\nYou MUST fix every error listed above! Ensure all nodes and connections detected from the PDF are present in elements and connections lists. Return ONLY valid JSON."
            )
            diagram_data = generate_text_json(retry_prompt, "diagram_builder_retry", max_tokens=8192, temperature=0.1, use_cache=False)

            is_valid, errors = _validate_diagram_schema(diagram_data, expected_vlm_regions=exp_regions, expected_vlm_connectors=exp_connectors) if diagram_data else (False, ["No JSON returned on retry"])

        if not is_valid:
            log.error(f"[diagram_builder] Diagram validation failed after 2 attempts for topic '{topic}': {errors}. MARKING DIAGRAM AS FAILED (NO FAKE STUB FALLBACK).")
            return {
                "has_programmatic_diagram": False,
                "diagram_error": f"Validation failed: {'; '.join(errors)}"
            }
            
        elements = diagram_data.get("elements", [])
        layout_preset = diagram_data.get("layout", "left_to_right")

        # ── FIX 3: FIDELITY FILTER ──────────────────────────────────────────
        # Drop any node/edge the LLM invented that the VLM did NOT see in the
        # PDF image, so the diagram only shows real nodes/connections/weights.
        _conns = diagram_data.get("connections", [])
        elements, _conns = _filter_to_vlm_confirmed(elements, _conns, exp_regions, exp_connectors)
        diagram_data["elements"] = elements
        diagram_data["connections"] = _conns

        # Enforce mathematical coordinate layout in Python (zero overlaps)
        assign_layout_coordinates(elements, layout_preset)

        
        svg_html = _build_svg(diagram_data)
        
        # Build word-to-ms lookup
        word_lookup = {}
        for wt in word_timestamps:
            if not isinstance(wt, dict) or "word" not in wt:
                continue
            clean_word = wt["word"].lower().strip(".,;:?!\"'-()")
            if clean_word and clean_word not in word_lookup:
                word_lookup[clean_word] = wt["start_ms"]
                
        def find_trigger_ms(keyword: str, fallback_ms: float) -> float:
            if not keyword:
                return fallback_ms
            keyword_clean = keyword.lower().strip(".,;:?!\"'-()")
            
            if keyword_clean in word_lookup:
                return word_lookup[keyword_clean]
            
            for w, ms in word_lookup.items():
                if w.startswith(keyword_clean) or keyword_clean.startswith(w):
                    return ms
                    
            for part in keyword_clean.split():
                if part in word_lookup:
                    return word_lookup[part]
                    
            return fallback_ms

        def get_appear_order(el):
            try:
                return int(el.get("appear_order", 1))
            except (ValueError, TypeError):
                return 1
                
        sorted_elements = sorted(elements, key=get_appear_order)
        
        events = []
        element_trigger_times = {}
        
        events.append({
            "event_type": "prog_diagram_overview",
            "timestamp_ms": 0.0,
            "start_ms": 0.0,
            "end_ms": 500.0,
            "data": {}
        })
        
        # Calculate evenly-spaced fallback interval based on audio duration
        audio_duration_ms = 10000.0
        if word_timestamps:
            last_wt = word_timestamps[-1]
            if isinstance(last_wt, dict) and "end_ms" in last_wt:
                audio_duration_ms = last_wt["end_ms"]
        
        total_animated = len([e for e in sorted_elements if e.get("initial") != "visible"])
        fallback_interval = (audio_duration_ms * 0.7) / max(total_animated, 1)
        
        for idx, el in enumerate(sorted_elements):
            eid = el.get("id")
            if not eid:
                continue
            keyword = el.get("trigger_keyword", "")
            
            # Smart fallback: evenly spaced across audio duration
            fallback_ms = 800.0 + idx * fallback_interval
            fallback_ms = min(fallback_ms, audio_duration_ms * 0.85)
                    
            trigger_ms = find_trigger_ms(keyword, fallback_ms)
            element_trigger_times[eid] = trigger_ms
            
            # For "visible" elements, show them at time 0
            if el.get("initial") == "visible":
                trigger_ms = 100.0 + idx * 50.0  # stagger slightly
                element_trigger_times[eid] = trigger_ms
            
            events.append({
                "event_type": "prog_node_appear",
                "timestamp_ms": trigger_ms,
                "start_ms": trigger_ms,
                "end_ms": trigger_ms + 800.0,
                "data": {
                    "element_id": eid,
                    "appear_order": el.get("appear_order", 1)
                }
            })
            
            events.append({
                "event_type": "prog_node_highlight",
                "timestamp_ms": trigger_ms + 200.0,
                "start_ms": trigger_ms + 200.0,
                "end_ms": trigger_ms + 1000.0,
                "data": {
                    "element_id": eid,
                    "color": el.get("color", "blue")
                }
            })
            
        connections = diagram_data.get("connections", [])
        el_map = {e["id"]: e for e in elements if "id" in e}
        for conn in connections:
            from_id = conn.get("from_id")
            to_id = conn.get("to_id")
            if not from_id or not to_id:
                continue
                
            from_el = el_map.get(from_id)
            to_el = el_map.get(to_id)
            if not from_el or not to_el:
                continue
                
            sx, sy, ex, ey = _get_connection_endpoints(from_el, to_el)
            length = ((ex - sx)**2 + (ey - sy)**2)**0.5
            conn_id = f"conn_{from_id}_{to_id}"
            
            from_ms = element_trigger_times.get(from_id, 1000.0)
            to_ms = element_trigger_times.get(to_id, from_ms + 800.0)
            # V17: Wait for BOTH source and destination nodes to be visible
            # before drawing the edge. Previously used from_ms + 800 which
            # could draw an arrow to a node that hasn't appeared yet.
            draw_ms = max(from_ms, to_ms) + 400.0
            
            events.append({
                "event_type": "prog_connection_draw",
                "timestamp_ms": draw_ms,
                "start_ms": draw_ms,
                "end_ms": draw_ms + 1000.0,
                "data": {
                    "connection_id": conn_id,
                    "length": round(length, 1),
                    "weight": conn.get("weight", "")
                }
            })
            
            # V17: Weight highlight event — pulse the weight badge after connection draws
            conn_weight = conn.get("weight", "")
            if conn_weight:
                weight_ms = draw_ms + 900.0
                events.append({
                    "event_type": "prog_weight_highlight",
                    "timestamp_ms": weight_ms,
                    "start_ms": weight_ms,
                    "end_ms": weight_ms + 800.0,
                    "data": {
                        "connection_id": conn_id,
                        "weight": str(conn_weight)
                    }
                })
            
        events.sort(key=lambda e: e["timestamp_ms"])
        
        # V16: Deletion events — nodes marked with deleted_at_step
        for el in elements:
            deleted_at = el.get("deleted_at_step")
            if deleted_at is not None and isinstance(deleted_at, (int, float)):
                delete_kw = el.get("delete_trigger_keyword", "")
                fallback_del = 1000.0 + (deleted_at * 1500.0)
                del_ms = find_trigger_ms(delete_kw, fallback_del)
                events.append({
                    "event_type": "prog_node_delete",
                    "timestamp_ms": del_ms,
                    "start_ms": del_ms,
                    "end_ms": del_ms + 1000.0,
                    "data": {
                        "element_id": el.get("id")
                    }
                })
        
        # V16: Insertion events — nodes with initial="animated" get green glow
        for el in elements:
            if el.get("initial") == "animated" and el.get("id") in element_trigger_times:
                ins_ms = element_trigger_times[el["id"]]
                events.append({
                    "event_type": "prog_node_insert",
                    "timestamp_ms": ins_ms,
                    "start_ms": ins_ms,
                    "end_ms": ins_ms + 1000.0,
                    "data": {
                        "element_id": el["id"]
                    }
                })
        
        # V18: Computation step events — floating text overlay
        comp_steps = diagram_data.get("computation_steps", [])
        for cs in comp_steps:
            step_kw = cs.get("trigger_keyword", "")
            step_text = cs.get("text", "")
            step_num = cs.get("step", 1)
            if not step_text:
                continue
            cs_fallback = 2000.0 + step_num * 1500.0
            cs_ms = find_trigger_ms(step_kw, cs_fallback)
            events.append({
                "event_type": "prog_compute_step",
                "timestamp_ms": cs_ms,
                "start_ms": cs_ms,
                "end_ms": cs_ms + 2000.0,
                "data": {
                    "step_num": step_num,
                    "text": step_text
                }
            })
        
        events.sort(key=lambda e: e["timestamp_ms"])
        
        return {
            "svg_html": svg_html,
            "animation_events": events,
            "has_programmatic_diagram": True,
            "element_count": len(elements),
            "connection_count": len(connections),
            "computation_steps": len(comp_steps)
        }
    except Exception as e:
        log.warning(f"Diagram builder failed: {e}")
        import traceback
        log.warning(traceback.format_exc())
        return {"has_programmatic_diagram": False}
