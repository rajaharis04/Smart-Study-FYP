"""
VLM Service - Groq LLaMA 4 Scout Vision Analysis for PDF Pages.

Uses Groq's multimodal model (meta-llama/llama-4-scout-17b-16e-instruct) to:
- Render each PDF page as an image
- Send the image to the Groq VLM API
- Get a structured description of graphs, tables, diagrams, and text layout
- Return enriched per-page metadata for use in the blueprint pipeline

This is the same VLM approach used in the existing lecture video pipeline,
now adapted for the 5-scene Blueprint Director system.
"""
import os
import base64
import uuid
from typing import List, Dict, Optional
from app.utils.logger import log_info, log_error, log_debug


def render_pdf_page_as_image(pdf_path: str, page_num: int, output_dir: str, dpi: int = 150) -> Optional[str]:
    """
    Render a single PDF page as a PNG image using PyMuPDF (fitz).
    Returns the saved image path or None if failed.
    """
    try:
        import fitz
        doc = fitz.open(pdf_path)
        if page_num >= len(doc):
            return None
        page = doc[page_num]
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        os.makedirs(output_dir, exist_ok=True)
        img_path = os.path.join(output_dir, f"page_{page_num + 1}_{uuid.uuid4().hex[:6]}.png")
        pix.save(img_path)
        doc.close()
        log_debug(f"Rendered PDF page {page_num + 1} → {img_path}")
        return img_path
    except Exception as e:
        log_error(f"Failed to render PDF page {page_num}: {e}")
        return None


def encode_image_base64(image_path: str) -> Optional[str]:
    """Encode image file as base64 string for API."""
    try:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        log_error(f"Failed to encode image {image_path}: {e}")
        return None


def analyze_page_with_vlm(image_path: str, groq_client, page_num: int) -> Dict:
    """
    Send a rendered PDF page image to the unified AI vision provider.
    Returns a structured dict with visual properties.
    """
    from core.ai_providers import analyze_image_json

    system_prompt = (
        "You are an expert educational content analyzer and diagram specialist. "
        "Analyze this PDF page image with extreme attention to detail.\n\n"
        "Return ONLY valid JSON with these exact keys:\n"
        "{\n"
        '  "page_type": "diagram|table|chart|text|mixed",\n'
        '  "has_diagram": true/false,\n'
        '  "has_table": true/false,\n'
        '  "has_chart": true/false,\n'
        '  "vlm_description": "EXTREMELY detailed description of what you see. For diagrams/graphs: list EVERY node with its exact label text, EVERY edge/arrow with source and destination labels, EVERY weight/distance/cost number on edges, and the overall spatial layout (left-to-right, top-to-bottom, circular, etc). For tables: describe columns, rows, and key data. Be as specific as possible — this description drives the entire video generation.",\n'
        '  "diagram_nodes": [{"label": "A", "type": "circle|rectangle|diamond", "position": "top-left|center|bottom-right"}],\n'
        '  "diagram_edges": [{"from": "A", "to": "B", "weight": "4", "label": "edge label", "directed": true}],\n'
        '  "diagram_layout": "left_to_right|top_to_bottom|radial|grid|tree|custom",\n'
        '  "has_edge_weights": true/false,\n'
        '  "has_distances": true/false,\n'
        '  "computation_steps": ["Step 1: Initialize source with d=0", "Step 2: Visit nearest unvisited node"],\n'
        '  "slide_title": "A short 6-word title summarizing this page",\n'
        '  "key_concepts": ["concept1", "concept2", "concept3"],\n'
        '  "pexels_supplement_keywords": ["abstract tech", "digital network"],\n'
        '  "dialogue_hint": "A 2-sentence teaching explanation of what is shown on this page",\n'
        '  "diagram_source_page": ' + str(page_num + 1) + '\n'
        "}\n\n"
        "CRITICAL RULES:\n"
        "1. For technical diagrams (graphs, trees, networks, flowcharts): describe EVERY SINGLE node label, "
        "EVERY SINGLE edge with its from/to labels, and EVERY weight/distance/cost number you can read. "
        "Do NOT summarize or skip any element.\n"
        "1b. FIDELITY — ONLY report what is ACTUALLY DRAWN in the image. Do NOT invent, guess, assume, or add "
        "any node, edge, weight, or label that you cannot literally see. Never add decorative/example/placeholder "
        "elements. If a value is unreadable, omit it rather than guessing. An empty accurate list is better than "
        "an invented one. Copy node labels and edge weights CHARACTER-FOR-CHARACTER as printed.\n"
        "2. For tables: describe ALL columns, ALL rows, and key data patterns.\n"

        "3. If there are computation steps shown (e.g., algorithm steps, distance calculations), list them in computation_steps.\n"
        "4. diagram_nodes and diagram_edges arrays must contain ALL visible nodes and edges — this data directly generates the video diagram.\n"
        "5. Never use nature metaphors for computer science content.\n"
        "6. pexels_supplement_keywords should be abstract tech keywords ONLY — never 'tree', 'forest', etc."
    )

    try:
        # 3000 tokens: dense diagram pages emit many nodes+edges+steps; 2000 was
        # truncating the JSON on complex pages and dropping detected elements.
        result = analyze_image_json(image_path, system_prompt, task_name=f"vlm_page_{page_num + 1}", max_tokens=3000)

        if not result or not isinstance(result, dict):
            raise ValueError("Empty or invalid JSON returned from unified provider")
            
        result["page_num"] = page_num + 1
        result["image_path"] = image_path
        log_info(f"VLM analyzed page {page_num + 1}: type={result.get('page_type', 'unknown')}")
        return result
    except Exception as e:
        log_error(f"VLM analysis failed for page {page_num + 1}: {e}")
        return _fallback_analysis(page_num)


def _fallback_analysis(page_num: int) -> Dict:
    """Fallback when VLM is unavailable."""
    return {
        "page_num": page_num + 1,
        "page_type": "text",
        "has_diagram": False,
        "has_table": False,
        "has_chart": False,
        "vlm_description": "Page content (VLM analysis unavailable)",
        "slide_title": f"Slide {page_num + 1}",
        "key_concepts": [],
        "pexels_supplement_keywords": ["technology abstract", "digital education"],
        "dialogue_hint": "This slide covers important educational content.",
        "image_path": None,
        "diagram_source_page": page_num + 1
    }


def process_pdf_with_vlm(pdf_path: str, groq_client, temp_dir: str, max_pages: int = 10) -> List[Dict]:
    """
    Full pipeline:
    1. Render each PDF page as an image
    2. Send to unified VLM provider for analysis
    3. Return list of enriched page analyses
    """
    import fitz
    results = []

    try:
        doc = fitz.open(pdf_path)
        total_pages = min(len(doc), max_pages)
        doc.close()
        log_info(f"Processing {total_pages} pages through VLM pipeline...")

        for page_idx in range(total_pages):
            img_path = render_pdf_page_as_image(pdf_path, page_idx, temp_dir)
            if img_path:
                analysis = analyze_page_with_vlm(img_path, groq_client, page_idx)
            else:
                analysis = _fallback_analysis(page_idx)
            results.append(analysis)

        log_info(f"VLM pipeline complete: {len(results)} pages analyzed")
        return results

    except Exception as e:
        log_error(f"process_pdf_with_vlm failed: {e}")
        return []


def analyze_diagram_with_vlm(image_path: str, groq_client=None) -> Dict:
    """
    Send an extracted diagram image to the unified AI vision provider.
    Requests bounding box coordinates [ymin, xmin, ymax, xmax] in normalized (0-1000) units
    for all key components, along with a 1-sentence explanation.
    """
    import hashlib
    import json
    
    try:
        with open(image_path, "rb") as f:
            file_hash = hashlib.md5(f.read()).hexdigest()
    except Exception:
        file_hash = hashlib.md5(image_path.encode()).hexdigest()

    cache_dir = os.path.join("static", "diagrams")
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = os.path.join(cache_dir, f"regions_{file_hash}.json")

    if os.path.exists(cache_path):
        log_info(f"[VLM Diagram Cache] Loading regions from cache: {cache_path}")
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log_error(f"[VLM Diagram Cache] Failed to load cache: {e}")

    from core.ai_providers import analyze_image_json

    system_prompt = """
You are an expert educational content analyst and spatial reasoning engine.
Analyze this PDF page image and return ONLY valid JSON — no markdown, no explanation.

For every diagram, table, chart, or visual element, identify each key component/region.

Return this exact schema:
{
  "page_type": "text|diagram|table|chart|equation|mixed",
  "has_visual": true,
  "main_concept": "one-line description of what this page teaches",
  "key_terms": ["term1", "term2", "term3"],
  "visual": {
    "type": "flowchart|block_diagram|bar_chart|line_chart|pie_chart|table|photo|equation|network",
    "title": "diagram title or null",
    "overall_bbox": {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0},
    "explanation_strategy": "left-to-right|top-to-bottom|center-out|sequential",
    "regions": [
      {
        "region_id": "input_node",
        "bbox": {"x": 0.05, "y": 0.10, "width": 0.20, "height": 0.15},
        "role": "input|process|decision|output|connector|other",
        "description": "receives raw input data from environment",
        "explanation_order": 1,
        "trigger_keyword": "input",
        "highlight_color": "blue"
      }
    ],
    "connectors": [
      {
        "connector_id": "arrow_input_to_step1",
        "from_region_id": "input_node",
        "to_region_id": "step1",
        "type": "arrow|line|dashed|curve",
        "path": [{"x": 0.25, "y": 0.26}, {"x": 0.3, "y": 0.26}],
        "label": "data flows",
        "explanation_order": 1,
        "trigger_keyword": "flows"
      }
    ],
    "flow_arrows": [
      {"from": "input_node", "to": "step1", "label": "data flows"}
    ],
    "key_insight": "one sentence a teacher would say about this diagram"
  },
  "table_data": {
    "headers": ["Col1", "Col2"],
    "rows": [["val1", "val2"]],
    "highlight_column": null,
    "key_row_index": 0
  },
  "equation": {
    "latex": "E = mc^2",
    "plain_text": "Energy equals mass times speed of light squared",
    "variables": [{"symbol": "E", "meaning": "Energy"}]
  },
  "teaching_sequence": [
    {
      "step": 1,
      "action": "overview",
      "target_component": null,
      "teacher_says": "Let me first show you the big picture..."
    },
    {
      "step": 2,
      "action": "zoom_to",
      "target_component": "input_node",
      "teacher_says": "Starting with the input layer..."
    }
  ]
}

CRITICAL RULES:
- FIDELITY FIRST — ONLY output nodes, connectors, weights, and labels that are LITERALLY VISIBLE in the image. NEVER invent, guess, assume, or add decorative/example/placeholder elements. Copy every node label and edge weight CHARACTER-FOR-CHARACTER as printed. If a label/weight is unreadable, omit it rather than guessing. An empty accurate list is better than an invented one. Do NOT output the sample region_ids/labels from the schema above unless they truly appear in the image.
- EXTRACT EVERY SINGLE NODE AND TEXT LABEL that IS present: identify and output ALL text labels, nodes, stages, steps, rows, columns, and shapes actually drawn. Do NOT summarize, skip, or group them.
- EXTRACT EVERY SINGLE CONNECTOR/ARROW that IS present: Every line or arrow connecting nodes must be listed under connectors with its exact from_region_id and to_region_id (both MUST reference a region_id you actually listed), along with a path. Do NOT invent connections that are not drawn.

- PEDAGOGICAL ORDER: Sort the regions and connectors in the logical chronological order in which a teacher would present them (e.g., following the flow of the process, input-to-output, or left-to-right).
- bbox x, y, width, and height values MUST be normalized 0.0-1.0 fractions of image size
- connectors path list points MUST be normalized 0.0-1.0 fractions of image size
- explanation_order follows the logical teaching sequence, not visual position
- trigger_keyword is the EXACT word from the narration that should activate this component/connector
- If no visual element exists, set has_visual to false and skip visual field
"""

    try:
        # 4000 tokens: this schema is large (regions + connectors + teaching
        # sequence). 2500 truncated on real diagrams, losing connectors/regions.
        result = analyze_image_json(image_path, system_prompt, task_name="vlm_diagram_analysis", max_tokens=4000)

        if not result or not isinstance(result, dict):
            raise ValueError("Empty or invalid JSON returned from unified provider")

        # Backward Compatibility Layer: map regions -> components
        if "visual" in result and isinstance(result["visual"], dict):
            vis = result["visual"]
            regions = vis.get("regions", [])
            if regions:
                components = []
                for r in regions:
                    bbox_obj = r.get("bbox", {})
                    # Convert object bbox to array bbox [x, y, width, height]
                    bbox_arr = [
                        bbox_obj.get("x", 0.0),
                        bbox_obj.get("y", 0.0),
                        bbox_obj.get("width", 0.2),
                        bbox_obj.get("height", 0.2)
                    ]
                    components.append({
                        "id": r.get("region_id", "comp_1"),
                        "label": r.get("region_id", "Component"),
                        "bbox": bbox_arr,
                        "description": r.get("description", ""),
                        "explanation_order": r.get("explanation_order", 1),
                        "trigger_keyword": r.get("trigger_keyword", ""),
                        "highlight_color": r.get("highlight_color", "blue")
                    })
                vis["components"] = components

            # Map legacy flow_arrows to connectors if connectors is empty
            connectors = vis.get("connectors", [])
            flow_arrows = vis.get("flow_arrows", [])
            if not connectors and flow_arrows:
                connectors = []
                for i, arrow in enumerate(flow_arrows):
                    from_id = arrow.get("from", "")
                    to_id = arrow.get("to", "")
                    connectors.append({
                        "connector_id": f"arrow_{from_id}_to_{to_id}",
                        "from_region_id": from_id,
                        "to_region_id": to_id,
                        "type": "arrow",
                        "path": [],
                        "label": arrow.get("label", ""),
                        "explanation_order": i + 1,
                        "trigger_keyword": arrow.get("label", "").split()[0] if arrow.get("label") else ""
                    })
                vis["connectors"] = connectors

        # Save to Cache
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            log_info(f"[VLM Diagram Cache] Saved regions to cache: {cache_path}")
        except Exception as cache_err:
            log_error(f"[VLM Diagram Cache] Failed to save cache: {cache_err}")

        log_info(f"VLM diagram analysis successful for {image_path}: found {len(result)} components.")
        return result

    except Exception as e:
        log_error(f"VLM diagram analysis failed for {image_path}: {e}")
        return {}

