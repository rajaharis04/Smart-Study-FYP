# -*- coding: utf-8 -*-
"""
SmartStudyInstructor V13 — Pedagogical Intelligence Engine
3.5-Agent LLM Pipeline:
  1. Content Analyst (Agent 1)
  2. Pedagogical Planner (Agent 2)
  3. DNA Classifier (Agent 1.5 - core/scene_dna.py)
  4. Scene Director (Agent 3 - DNA-Aware)
"""
import json
import random
from typing import Dict, List, Optional
from app.utils.logger import log_info, log_error
from core.scene_dna import classify_scene_dna

AGENT3_QUALITY_RULES = """
CRITICAL QUALITY RULES — VIOLATING ANY OF THESE MEANS THE OUTPUT IS REJECTED:

RULE 1 — NEVER start narration with the same word as any other scene. Rotate through these openers, never repeating consecutively:
- A surprising fact: "Here is something most students get wrong..."
- A direct question: "What actually happens when...?"  
- A real-world connection: "Think about the last time you..."
- A contrast: "Unlike what you might expect..."
- A consequence: "Get this wrong and the entire system fails..."
- A challenge: "This is the part that trips everyone up..."
- A discovery: "Scientists discovered something unexpected here..."

RULE 2 — DEEP EXPLANATION & DOMAIN EXPERTISE:
Do NOT just summarize or read the PDF text. You are a world-class Master Professor. Combine the PDF facts and diagram analysis with your VAST INTERNAL DOMAIN KNOWLEDGE. Explain:
- WHY this concept works under the hood
- Real-world analogies and intuitive physical/mental models
- Step-by-step mathematical, logical, or architectural mechanisms
- Edge cases, common pitfalls, and practical industry applications

RULE 3 — EVERY NARRATION FOLLOWS THIS 4-PART ARC (8-12 Sentences Total):
1. HOOK (sentences 1-2): Use mandatory opening phrase + intriguing real-world scenario/question.
2. EXPLAIN & INTUITION (sentences 3-6): Deeply explain the core mechanics, underlying principles, and intuitive analogies using your domain knowledge.
3. DEMONSTRATE & VISUAL WALKTHROUGH (sentences 7-10): Walk through the diagram, formula, or process step-by-step. Name visual nodes/connectors/variables explicitly in chronological order.
4. REINFORCE & TAKEAWAY (sentences 11-12): Synthesize into a memorable takeaway and link to the broader subject.

RULE 4 — WORD COUNT REQUIREMENT: MINIMUM 180 WORDS, MAXIMUM 260 WORDS.
Deliver a rich, full, lecture-length narration script. Never write a short 2-3 sentence summary! Count your words before returning.

RULE 5 — THE GOLD WORD: The gold_word must appear naturally in your narration in a position of emphasis.

RULE 6 — BULLETS DERIVATION: Bullets will be extracted directly from your EXPLAIN section. Ensure sentences 3-6 contain 3-4 clear, high-value, crisp insights.

RULE 7 — DIAGRAM NARRATION SYNC (for diagram_only and bullets_then_diagram scenes):
If scene_mode is "diagram_only" or "bullets_then_diagram", every sentence in the DEMONSTRATE section must describe one visual element/step appearing on screen. The narration word order must match the diagram_step_sequence exactly so elements animate at the exact spoken moment.
"""

# Add at module level in pedagogical_engine.py
OPENING_HOOK_INVENTORY = {
    "CONCEPT_DEFINITION": [
        "Here is a question most people get wrong on their first try —",
        "Before {year}, nobody had a word for this. Now it runs everything —",
        "Strip away the jargon and you are left with one simple idea —",
        "The textbook definition misses the point. Here is what actually matters —",
        "Most students memorize this. The best students understand why it exists —",
        "Picture this scenario for a moment —",
        "There is one word in this topic that changes everything —",
        "If you only remember one thing from this entire lecture, make it this —",
        "This concept confuses almost everyone at first. Here is why —",
        "You already understand this without knowing it. Here is the proof —",
    ],
    "PROCESS_FLOW": [
        "Watch what happens when we follow this step by step —",
        "Every single time this runs, it follows the same path —",
        "The order matters more than the steps themselves. Here is why —",
        "Start at the beginning and do not skip anything —",
        "Think of this as a recipe where getting the sequence wrong ruins everything —",
        "Step one sets up everything that follows. Pay close attention —",
        "This process has a hidden elegance once you see the full picture —",
        "Trace this from input to output and the whole system becomes clear —",
        "Three stages. Each one depends on the last. Let us walk through them —",
        "At each stage, one specific thing happens. Nothing more, nothing less —",
    ],
    "CAUSE_EFFECT": [
        "One event triggers everything else in this chain —",
        "Remove the cause and the effect disappears entirely —",
        "The relationship here is not a coincidence. It is a mechanism —",
        "This is not a correlation. This is a direct cause —",
        "Something specific happens, and because of it, something else must follow —",
        "The effect is dramatic. The cause is surprisingly simple —",
        "Most people see the effect. Very few ask what caused it —",
        "Here is what nobody tells you about why this happens —",
        "There is a reason this always leads to the same outcome —",
        "Change the cause and you change the effect. That is the whole lesson —",
    ],
    "COMPARISON": [
        "These two look similar on the surface. Underneath, they are completely different —",
        "Side by side, the contrast becomes impossible to ignore —",
        "One handles this situation well. The other fails completely. Here is why —",
        "The difference between these two is not just academic. It changes outcomes —",
        "Choosing the wrong one for the wrong job is one of the most common mistakes —",
        "On paper they seem equivalent. In practice, everything changes —",
        "Let us hold these up next to each other and see what falls apart —",
        "The key distinction is not size or speed. It is something more fundamental —",
        "Both do the same job. Only one does it well under these conditions —",
        "Understanding the difference here separates beginners from experts —",
    ],
    "DIAGRAM_SPATIAL": [
        "Before we go into detail, step back and look at the whole picture —",
        "Every component in this diagram has exactly one job —",
        "Start with the overview. The details will make much more sense afterward —",
        "Each piece connects to the others. Nothing here is isolated —",
        "Look at where the arrows point. They tell the whole story —",
        "The structure here is not random. There is a reason for every placement —",
        "Zoom out first. Then we go in deep on each part —",
        "This diagram has three layers. Once you see them, you cannot unsee them —",
        "Follow the flow from left to right and everything clicks into place —",
        "The most important component is not the biggest one on this diagram —",
    ],
    "WORKED_EXAMPLE": [
        "Do not memorize this formula. Understand what each part is doing —",
        "Every symbol in this equation is earning its place. Here is how —",
        "Work through this once carefully and you will never forget it —",
        "The formula looks complex. Break it down and it becomes obvious —",
        "Left side, right side. One question: what does each side represent —",
        "Plug in a real number and the abstraction disappears —",
        "The trick is not calculation. The trick is knowing what you are calculating —",
        "Read this like a sentence, not like arithmetic —",
        "Three terms. Each one tells you something different about the system —",
        "This formula is actually a compressed story. Let us decompress it —",
    ],
    "ANALOGY_BRIDGE": [
        "You already understand something that works exactly like this —",
        "Before we touch the technical concept, here is a scenario you know well —",
        "The analogy is not perfect. But it gets you ninety percent of the way there —",
        "If you have ever done this in real life, you already get the concept —",
        "Forget the technical name for a moment. Think about this instead —",
        "The same principle is at work in both situations. Watch —",
        "Once you see the similarity, the formal definition becomes easy —",
        "This concept borrows its logic from something completely ordinary —",
        "The real-world version and the technical version follow identical rules —",
        "Start with what you know, then move to what you are learning —",
    ],
    "TAKEAWAY_SUMMARY": [
        "Everything covered so far comes down to this single point —",
        "If the exam asked one question about this topic, here is the answer —",
        "This is the part worth writing down —",
        "Reduce everything to its core and you get this —",
        "Forget the details for a second. What is the one thing that matters —",
        "The whole topic exists to support this conclusion —",
        "This is what separates understanding from just knowing —",
        "Three words. That is all it takes to capture this idea —",
        "Come back to this if you forget everything else —",
        "The essence. Not the definition. The actual insight —",
    ],
}

def _derive_bullets_from_narration(narration_text: str, dna_type: str) -> list:
    """
    Bullets must come FROM the narration — not be invented separately.
    
    V16: Extracts bullets from the EXPLAIN section (sentences 2-5) of the
    narration's 4-part arc (Hook→Explain→Demonstrate→Reinforce).
    Bullets appear during the explanation phase only — NOT during diagram walkthrough.
    
    Called AFTER narration is generated, not before.
    """
    import re as _re
    
    # Split narration into sentences
    sentences = [s.strip() for s in _re.split(r'(?<=[.!?])\s+', narration_text) if len(s.strip()) > 20]
    
    if not sentences:
        return [{"text": "Key concept introduced", "zoom_word": "concept", "trigger_word": "concept", "entrance": "slide_left", "num": "01"}]
    
    # 4-part arc: Hook(1-2) → Explain(3-5) → Demonstrate(6-8) → Reinforce(9-10)
    # Bullets come from the EXPLAIN section only (skip hook, skip demonstrate/reinforce)
    total = len(sentences)
    if total >= 8:
        # Full narration: skip first 2 (hook), take sentences 3-6 (explain), skip rest (demonstrate+reinforce)
        explain_sentences = sentences[2:6]
    elif total >= 5:
        # Medium narration: skip first 1 (hook), take sentences 2-5 (explain), skip last (reinforce)
        explain_sentences = sentences[1:5]
    else:
        # Short narration: skip first if possible, take what's left
        explain_sentences = sentences[1:] if total > 2 else sentences
    
    # Select 3-4 bullets max
    selected = explain_sentences[:4]
    
    # Expanded stopwords for better zoom_word selection
    stopwords = {
        'their', 'these', 'those', 'there', 'where', 'which', 'while', 'about',
        'would', 'could', 'should', 'think', 'begin', 'start', 'first', 'every',
        'other', 'after', 'before', 'under', 'above', 'between', 'through',
        'means', 'makes', 'takes', 'works', 'looks', 'comes', 'needs',
        'really', 'simply', 'actually', 'exactly', 'notice', 'called'
    }
    
    bullets = []
    for i, sent in enumerate(selected):
        bullet_text = sent.strip()
        if bullet_text and not bullet_text[0].isupper():
            bullet_text = bullet_text[0].upper() + bullet_text[1:]
        
        # Pick the most technical/specific word as zoom_word
        # Prefer longer words that aren't common verbs/adverbs
        bullet_words = bullet_text.split()
        zoom_candidates = [
            w for w in bullet_words 
            if len(w) > 4 and w.lower().strip('.,;:?!-"\'()') not in stopwords
        ]
        
        if zoom_candidates:
            # Prefer words that look technical (capitalized mid-sentence or long)
            technical = [w for w in zoom_candidates if w[0].isupper() and i > 0]
            zoom_word = max(technical or zoom_candidates, key=len)
        else:
            zoom_word = bullet_words[-1] if bullet_words else "concept"
        
        zoom_word_clean = zoom_word.strip('.,;:?!-"\'()').lower()
        
        bullets.append({
            "text": bullet_text.strip().rstrip('.'),
            "zoom_word": zoom_word_clean,
            "trigger_word": zoom_word_clean,
            "entrance": "slide_left",
            "num": f"{i+1:02d}"
        })
    
    return bullets if bullets else [{"text": "Key concept introduced", "zoom_word": "concept", "trigger_word": "concept", "entrance": "slide_left", "num": "01"}]

def _validate_script_diversity(scenes: list) -> list:
    """
    Post-generation validator. Checks and fixes:
    1. No two scenes start with the same first word
    2. No two consecutive scenes use the same DNA narration opener pattern
    3. gold_word actually appears in narration
    4. Bullet zoom_word actually appears in bullet text
    5. No banned filler phrases in narration
    6. Programmatic enforcement of DNA-specific keywords (PROCESS_FLOW, CAUSE_EFFECT, COMPARISON)
    """
    import re
    import logging
    logger = logging.getLogger("pedagogical_engine")
    
    seen_openers = {}  # {first_word: scene_id}
    banned_phrases = ["in conclusion", "in summary", "as we can see", "it is worth noting", "essentially", "basically"]
    
    for i, scene in enumerate(scenes):
        narration = scene.get("narration", "")
        if not narration:
            continue
        
        # Check 5: Remove filler/banned phrases case-insensitively
        for phrase in banned_phrases:
            if phrase in narration.lower():
                narration = re.sub(re.escape(phrase), "", narration, flags=re.IGNORECASE)
                # Clean up any double spaces or punctuation mess left behind
                narration = narration.replace("  ", " ").replace(", ,", ",").replace("..", ".").strip()
        
        # Check 1: First word uniqueness
        first_word = narration.strip().split()[0].lower().rstrip(".,;:?!-")
        if first_word in seen_openers:
            # First word collision! Prepend a unique transition word to break the tie
            transitions = ["Now, ", "So, ", "Next, ", "Well, ", "Indeed, ", "Observe: ", "Remember, "]
            picked_transition = ""
            for t in transitions:
                clean_t = t.lower().rstrip(".,;:?!- ")
                if clean_t not in seen_openers:
                    picked_transition = t
                    break
            else:
                picked_transition = "And, "
            
            narration = picked_transition + narration
            first_word = narration.strip().split()[0].lower().rstrip(".,;:?!-")
            logger.warning(f"[Diversity Validator] Fixed duplicate first word opener on {scene['scene_id']} by prepending '{picked_transition.strip()}'")
        
        seen_openers[first_word] = scene["scene_id"]
        
        # Check 6: Programmatic enforcement of DNA-specific keywords
        clean_dna = scene.get("scene_dna", {}).get("dna_type", "")
        if " " in clean_dna:
            clean_dna = clean_dna.split(" ", 1)[1]
        elif "-" in clean_dna:
            clean_dna = clean_dna.split("-", 1)[1]

        if clean_dna == "PROCESS_FLOW":
            flow_keywords = ['first', 'then', 'next', 'finally', 'step']
            matches = [w for w in flow_keywords if w in narration.lower()]
            if len(matches) < 2:
                narration = narration.rstrip(". ") + ". Next, we follow the final step to complete the flow."
                logger.info(f"[Diversity Validator] Injected process flow transition words into scene {scene['scene_id']}")
        
        elif clean_dna == "CAUSE_EFFECT":
            cause_keywords = ['because', 'leads to', 'results in', 'therefore', 'causes']
            matches = [w for w in cause_keywords if w in narration.lower() or any(phrase in narration.lower() for phrase in ['leads to', 'results in'])]
            if not matches:
                narration = narration.rstrip(". ") + ". Therefore, this cause directly triggers the final effect."
                logger.info(f"[Diversity Validator] Injected cause-effect transition words into scene {scene['scene_id']}")
                
        elif clean_dna == "COMPARISON":
            comp_keywords = ['unlike', 'whereas', 'difference', 'contrast', 'compared']
            matches = [w for w in comp_keywords if w in narration.lower()]
            if not matches:
                narration = narration.rstrip(". ") + ". In contrast, the key difference is easy to see compared to others."
                logger.info(f"[Diversity Validator] Injected comparison transition words into scene {scene['scene_id']}")

        # Ensure narration is stored back
        scene["narration"] = narration

        # Check 2: gold_word in narration
        gold = scene.get("gold_word", "").lower()
        if not gold or gold not in narration.lower():
            stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'and', 'or', 
                         'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'this',
                         'that', 'these', 'those', 'then', 'here', 'there', 'what', 'why', 'how'}
            narration_words = [w.strip(".,;:?!-").lower() for w in narration.split() if w.strip(".,;:?!-").lower() not in stop_words]
            candidates = [w for w in narration_words if len(w) > 5]
            if candidates:
                scene["gold_word"] = max(candidates, key=len)
            elif narration_words:
                scene["gold_word"] = max(narration_words, key=len)
            else:
                scene["gold_word"] = "concept"
        
        # Check 3: zoom_word in bullet text and trigger_word in narration
        for bullet in scene.get("bullets", []):
            zoom = bullet.get("zoom_word", "").lower()
            bullet_text = bullet.get("text", "").lower()
            if not zoom or zoom not in bullet_text:
                words = [w.strip(".,;:?!-").lower() for w in bullet_text.split() if len(w) > 3]
                if words:
                    zoom = max(words, key=len)
                else:
                    zoom = bullet_text.split()[-1].strip(".,;:?!-").lower() if bullet_text.split() else "key"
                bullet["zoom_word"] = zoom
            
            bullet["trigger_word"] = zoom

    return scenes

class PedagogicalEngine:
    """
    Splits blueprint generation into focused, DNA-driven pedagogical steps.
    Translates raw materials into highly engaging structured scenes.
    """

    def __init__(self, llm_client):
        """
        Args:
            llm_client: Any LLMClient instance supporting _chat(system, user, max_tokens)
        """
        self._llm = llm_client

    # ──────────────────────────────────────────────────────────────────────
    # Agent 1: Content Analyst
    # ──────────────────────────────────────────────────────────────────────

    def analyze_content(self, document_text: str, vlm_pages: List[Dict] = None) -> Dict:
        """Analyzes raw document text and returns a structured content map."""
        vlm_context = ""
        if vlm_pages:
            summaries = []
            for p in vlm_pages:
                page_info = f"[Page {p.get('page_num')} | {p.get('page_type')}] {p.get('vlm_description', '')}"
                # Include structured node/edge data from enhanced VLM
                nodes = p.get('diagram_nodes', [])
                edges = p.get('diagram_edges', [])
                if nodes:
                    node_labels = [n.get('label', '?') for n in nodes]
                    page_info += f"\n  Diagram Nodes: {', '.join(node_labels)}"
                if edges:
                    edge_strs = [f"{e.get('from','?')}→{e.get('to','?')}" + (f" (w={e.get('weight','')})" if e.get('weight') else "") for e in edges]
                    page_info += f"\n  Diagram Edges: {'; '.join(edge_strs)}"
                if p.get('has_edge_weights'):
                    page_info += "\n  Has Edge Weights: YES"
                if p.get('computation_steps'):
                    page_info += f"\n  Computation Steps: {'; '.join(p.get('computation_steps', []))}"
                summaries.append(page_info)
            vlm_context = "\n=== VISUAL ANALYSIS (VLM Extracted from PDF Images) ===\n" + "\n".join(summaries)

        system = """You are a master educator and content analyst. You have received a complete PDF document to teach.

YOUR TASK — Do this in order:

STEP 1 — UNDERSTAND THE WHOLE DOCUMENT (TEXT + DIAGRAMS TOGETHER):
Read everything - the full text AND every diagram in the VLM analysis. What is the main subject? What are the 3 to 10 major concepts a student must learn from this document?
Now decide the BEST EXPLANATION ORDER: order teaching_units so each concept builds on its prerequisites (foundational/definition scenes first, then applications, then summary). A concept and the diagram that explains it must live in the SAME teaching_unit (keep them adjacent, never separate a diagram from the concept it illustrates). Only mark a scene as needing a diagram when a visual is genuinely essential to understanding OR the PDF actually provides one for that concept - do NOT request a diagram just to fill space.

STEP 2 — DECIDE SCENE COUNT:
Let the document content decide. Simple short documents: 3-5 scenes. Complex technical documents: 7-12 scenes. Very long documents: up to 20 scenes. Never hardcode a number.

STEP 3 — FOR EACH SCENE, DECIDE THE MODE:
- "bullets_only" — if this concept can be fully understood through explanation alone
- "diagram_only" — if a visual is essential to understanding, OR if the PDF has a diagram for this concept
- "bullets_then_diagram" — if a 1-2 sentence intro with bullets helps before seeing the diagram

STEP 4 — FOR DIAGRAM SCENES, DESCRIBE EXACTLY WHAT TO DRAW:
Look at the VLM analysis for that page. Describe in detail:
- What type of diagram is it? (flowchart, graph, tree, biological, circuit, process, timeline, comparison, formula)
- What nodes/components exist? What are their labels?
- How are they connected? What do the arrows or lines mean?
- Are there weights, distances, or labels on connections?
- Does the explanation involve elements appearing one by one, or being inserted, or being deleted?
- What is the correct step-by-step order to reveal elements?

Return ONLY a JSON object containing:
{
  "course_title": "main subject of the document",
  "document_summary": "2 sentences describing the full document",
  "main_topics": ["array of topic strings in teaching order"],
  "concept_dependency_graph": [{"concept": "X", "depends_on": ["Y"]}],
  "difficulty_progression": ["beginner or intermediate or advanced per topic"],
  "diagram_page_numbers": [integers if visuals present],
  "prerequisite_gaps": "string describing what prior knowledge students need",
  "has_equations": true or false,
  "has_tables": true or false,
  "equation_topics": ["topic names that contain math/formulas"],
  "table_topics": ["topic names that have tabular data"],
  "total_estimated_scenes": integer,
  "teaching_units": [
    {
      "unit_id": 1,
      "topic": "specific topic of this scene",
      "core_concept": "the single most important idea to teach",
      "scene_mode": "bullets_only or diagram_only or bullets_then_diagram",
      "source_pages": [1, 2],
      "has_diagram": true or false,
      "diagram_type": "flowchart or graph or tree or biological or circuit or process or timeline or comparison or formula or none",
      "diagram_description": "detailed 4-5 sentence description of the diagram: type, all elements, connections, labels, teaching order",
      "diagram_step_sequence": ["first show X", "then show Y connecting to Z", "then delete W"],
      "has_insertions": true or false,
      "has_deletions": true or false,
      "has_edge_weights": true or false,
      "teaching_hook": "a surprising fact or question to open this scene with",
      "difficulty": "introductory or intermediate or advanced"
    }
  ]
}"""

        from core.ai_providers import generate_text_json_premium
        prompt = f"{system}\n\n{vlm_context}\n\nDOCUMENT:\n{document_text[:12000]}"
        try:
            result = generate_text_json_premium(prompt, task_name="agent1_content_analyst", max_tokens=4096)

            if not result or not isinstance(result, dict):
                raise ValueError("Empty or invalid JSON returned from unified provider")
            log_info(f"[V13 Agent 1] Content Analysis: {result.get('total_estimated_scenes', '?')} scenes suggested")
            return result
        except Exception as e:
            log_error(f"[V13 Agent 1] Parse error: {e}")
            return {"concept_dependency_graph": [], "total_estimated_scenes": 5,
                    "course_title": "Unknown", "main_topics": []}

    # ──────────────────────────────────────────────────────────────────────
    # Agent 2: Pedagogical Planner
    # ──────────────────────────────────────────────────────────────────────

    def plan_pedagogy(self, content_analysis: Dict, document_text: str) -> Dict:
        """Decides overall narrative strategy and learning progressions."""
        system = """You are a World-Class Pedagogical Architect trained in Mayer's Multimedia Learning Principles, Socratic Scaffolding, and Cognitive Load Theory. 
Your goal is to transform the content analysis into an elegant, high-impact instructional plan. We want the student to have an active learning experience, NOT feel like they are watching the news.

For each concept in the content analysis, you must plan a custom pedagogical strategy:
1. "explanation_strategy": Choose from:
   - "first_principles": strip away all jargon and derive the concept from the absolute ground up.
   - "analogy_bridging": start with a powerful, relatable everyday analogy, then bridge to the technical details.
   - "socratic_challenge": start with a paradox or question that exposes a gap in the student's current model, then build the concept to solve it.
   - "visual_flowchart": heavily emphasize visual connections, drawing circles/arrows on diagrams first.
2. "expected_confusion_point": pinpoint the exact cognitive trap or common misconception students fall into for this topic.
3. "aha_moment_trigger": describe the precise conceptual breakthrough, metaphor, or visualization that immediately makes the concept click.
4. "pacing_note": "fast"/"normal"/"slow" based on cognitive difficulty, with a pedagogical reason.
5. "narrative_tone": Choose one: "storyteller", "socratic_mentor", "intuitive_scientist", "enthusiastic_engineer".
6. "animation_priority": "diagram", "bullets", or "both".

Return a single JSON object containing:
- "teaching_strategies": array of the above planned strategies per concept.
- "global_pacing_notes": general strategy to prevent cognitive overload.
- "narrative_arc": how the concepts connect to tell a unified pedagogical story.
Return ONLY valid JSON. No markdown, no explanations."""

        from core.ai_providers import generate_text_json_premium
        concepts_summary = json.dumps(content_analysis, indent=2)
        prompt = f"{system}\n\nCONTENT ANALYSIS:\n{concepts_summary}\n\nDOCUMENT EXCERPT:\n{document_text[:4000]}"
        try:
            result = generate_text_json_premium(prompt, task_name="agent2_pedagogical_planner", max_tokens=2048)
            if not result or not isinstance(result, dict):
                raise ValueError("Empty or invalid JSON returned from unified provider")
            strategies = result.get("teaching_strategies", [])
            log_info(f"[V13 Agent 2] Pedagogy Plan: {len(strategies)} strategies, arc={result.get('narrative_arc', '?')}")
            return result
        except Exception as e:
            log_error(f"[V13 Agent 2] Parse error: {e}")
            return {"teaching_strategies": [], "narrative_arc": "building_blocks"}

    # ──────────────────────────────────────────────────────────────────────
    # Agent 3: DNA-Aware Scene Director
    # ──────────────────────────────────────────────────────────────────────

    def direct_scenes(
        self,
        pedagogy_plan: Dict,
        content_analysis: Dict,
        document_text: str,
        extracted_images: List[str] = None,
        diagram_spatial_data: Dict = None,
        vlm_pages: List[Dict] = None,
    ) -> Dict:
        """
        Generates the final Blueprint V5 JSON utilizing the new Scene DNA Classifier.
        This Scene Director is fully DNA-aware and prompts Agent 3 dynamically per scene
        to produce highly diverse scripts and correct animation metadata.
        """
        log_info("[V15 Agent 3] Launching DNA-aware Scene Director...")
        
        # 1. Map content chunks to separate scene blueprints sequentially
        main_topics = content_analysis.get("main_topics", [])
        if not main_topics:
            main_topics = ["Introduction", "Core Principles", "Applications", "Summary"]

        # ── UPGRADE 1: Dynamic Scene Count Planning ──
        estimated_scenes = content_analysis.get("total_estimated_scenes", len(main_topics))
        estimated_scenes = max(len(main_topics), min(int(estimated_scenes), 20))  # clamp: never drop topics, max 20
        
        # If LLM recommends more scenes than topics, subdivide topics proportionally
        if estimated_scenes > len(main_topics):
            expanded_topics = []
            per_topic = max(1, estimated_scenes // len(main_topics))
            remainder = estimated_scenes - (per_topic * len(main_topics))
            for ti, t in enumerate(main_topics):
                count = per_topic + (1 if ti < remainder else 0)
                if count == 1:
                    expanded_topics.append(t)
                else:
                    for sub in range(count):
                        expanded_topics.append(f"{t} — Part {sub + 1}")
            main_topics = expanded_topics[:estimated_scenes]
            log_info(f"[V15] Expanded {len(content_analysis.get('main_topics', []))} topics → {len(main_topics)} scenes (LLM recommended {estimated_scenes})")
        
        total_scenes = len(main_topics)
        scenes = []

        doc_len = len(document_text)

        # ── UPGRADE 3: VLM-Guided Diagram Assignment ──
        # Build topic→diagram mapping using VLM keyword overlap
        _assigned_diagrams = set()
        def _find_best_diagram_for_topic(topic_name: str, scene_idx: int) -> tuple:
            """Resolve a matching diagram image for a topic - WITHOUT forcing one.

            FIX 4 - Per-scene diagram decision belongs to the Agent, not to code.
            This helper NO LONGER round-robin-assigns a leftover image to every
            scene. It only returns a diagram when there is a genuine semantic
            match between the topic and a VLM-analyzed page. If nothing matches,
            it returns (False, "") and the caller decides based on the Agent's
            explicit intent (scene_mode / has_diagram).
            """
            if not extracted_images:
                return False, ""

            # ONLY strategy: VLM keyword overlap (genuine semantic match).
            if vlm_pages:
                best_score = 0
                best_path = ""
                topic_words = set(topic_name.lower().split())
                for vp in vlm_pages:
                    img_path = vp.get("image_path", "")
                    if not img_path or img_path in _assigned_diagrams:
                        continue
                    if img_path not in extracted_images:
                        continue
                    # Score by keyword overlap
                    key_concepts = [k.lower() for k in vp.get("key_concepts", [])]
                    vlm_desc_words = set(vp.get("vlm_description", "").lower().split()[:50])
                    concept_set = set(key_concepts) | vlm_desc_words
                    overlap = len(topic_words & concept_set)
                    # Bonus for exact concept match
                    for kc in key_concepts:
                        if kc in topic_name.lower():
                            overlap += 3
                    if overlap > best_score:
                        best_score = overlap
                        best_path = img_path
                if best_score > 0 and best_path:
                    _assigned_diagrams.add(best_path)
                    return True, best_path

            # No genuine match -> do NOT force a diagram onto this scene.
            return False, ""

        def _claim_any_unused_diagram() -> str:
            """Claim an extracted image when the Agent explicitly asked for a
            diagram but VLM keyword matching found none.

            Prefers a not-yet-assigned image (spread coverage across pages), but
            if every image is already assigned it REUSES one via round-robin
            instead of returning "". Rationale: a short PDF often renders to just
            1-2 page images while explaining ONE diagram (e.g. a Dijkstra graph)
            across many scenes. Blocking reuse used to downgrade scenes 3+ to
            bullets_only even though the same graph image is exactly what those
            scenes need. Reuse keeps the diagram on-screen for every scene the
            Agent wanted it."""
            if not extracted_images:
                return ""
            # First choice: an unused image.
            for img in extracted_images:
                if img not in _assigned_diagrams:
                    _assigned_diagrams.add(img)
                    return img
            # All assigned -> reuse round-robin so no scene is starved.
            idx = getattr(self, "_diagram_reuse_counter", 0)
            self._diagram_reuse_counter = idx + 1
            return extracted_images[idx % len(extracted_images)]


        valid_scenes_count = 0
        for i, topic_name in enumerate(main_topics):
            if doc_len < 4000:
                content_chunk = document_text
            else:
                chunk_sz = doc_len // max(1, total_scenes)
                start_idx = i * chunk_sz
                # Provide a generous overlap
                end_idx = min(start_idx + chunk_sz + 1000, doc_len)
                content_chunk = document_text[start_idx:end_idx]

            if not content_chunk.strip():
                log_info(f"Skipping topic '{topic_name}' because text chunk is empty.")
                continue

            # ── V16: Look up Agent 1 teaching_units for scene_mode + diagram metadata ──
            # FIX 4 - The AGENT (Agent 1) is the single source of truth for whether
            # a scene needs a diagram. We resolve the unit FIRST, then decide.
            _teaching_units = content_analysis.get("teaching_units", [])
            _agent1_unit = None

            # FIX: Robust topic↔teaching_unit matching
            # Strip "— Part N" suffix for normalized comparison
            import re as _re_match
            def _normalize_topic(t: str) -> str:
                return _re_match.sub(r'\s*[—–-]+\s*Part\s*\d+\s*$', '', t, flags=_re_match.IGNORECASE).strip().lower()

            _norm_topic = _normalize_topic(topic_name)

            if _teaching_units:
                # Pass 1: exact normalized-name match (handles "— Part N" expanded topics)
                for _tu in _teaching_units:
                    if _normalize_topic(_tu.get("topic", "")) == _norm_topic:
                        _agent1_unit = _tu
                        break

                # Pass 2: index-based fallback (only when normalized match fails)
                if _agent1_unit is None and i < len(_teaching_units):
                    _agent1_unit = _teaching_units[i]

                # Pass 3: substring fuzzy match (last resort)
                if _agent1_unit is None:
                    for _tu in _teaching_units:
                        _tu_norm = _normalize_topic(_tu.get("topic", ""))
                        if _tu_norm in _norm_topic or _norm_topic in _tu_norm:
                            _agent1_unit = _tu
                            break

            # V16: scene_mode from Agent 1 (AI decides, not code)
            _scene_mode = "bullets_only"  # safe default
            _valid_modes = {"bullets_only", "diagram_only", "bullets_then_diagram"}
            if _agent1_unit:
                _raw_mode = _agent1_unit.get("scene_mode", "bullets_only")
                _scene_mode = _raw_mode if _raw_mode in _valid_modes else "bullets_only"

            # ── FIX 4: Agent-first diagram decision (NO forcing) ──
            # A scene wants a diagram ONLY if the Agent explicitly said so via
            # has_diagram=True OR a diagram-bearing scene_mode. If the Agent gave
            # no opinion (no teaching_units), we fall back to a genuine VLM match.
            _agent_wants_diagram = bool(
                _agent1_unit and (
                    _agent1_unit.get("has_diagram") is True
                    or _scene_mode in ("diagram_only", "bullets_then_diagram")
                )
            )

            has_diagram = False
            diagram_path = ""

            if _agent_wants_diagram:
                # Agent asked for a diagram -> try to resolve a real image for it.
                _matched, _matched_path = _find_best_diagram_for_topic(topic_name, i)
                if _matched:
                    has_diagram, diagram_path = True, _matched_path
                else:
                    # No semantic match - claim any unused extracted image so the
                    # agent's explicit intent is honored with a real asset.
                    _claimed = _claim_any_unused_diagram()
                    if _claimed:
                        has_diagram, diagram_path = True, _claimed
                    else:
                        # No images available at all -> gracefully downgrade so we
                        # never render a blank/fullscreen diagram placeholder.
                        has_diagram, diagram_path = False, ""
                        if _scene_mode in ("diagram_only", "bullets_then_diagram"):
                            log_info(f"[FIX4 Scene {i+1}] Agent wanted {_scene_mode} but no image available -> downgraded to bullets_only")
                            _scene_mode = "bullets_only"
            elif not _agent1_unit:
                # No Agent guidance at all (e.g. Agent 1 returned no teaching_units).
                # Fall back to a GENUINE VLM keyword match only - still no forcing.
                _matched, _matched_path = _find_best_diagram_for_topic(topic_name, i)
                if _matched:
                    has_diagram, diagram_path = True, _matched_path
                    _scene_mode = "bullets_then_diagram"
            # else: Agent explicitly did NOT want a diagram -> leave has_diagram=False.

            log_info(f"[V16 Scene {i+1}] scene_mode={_scene_mode} | has_diagram={has_diagram} | agent_wants_diagram={_agent_wants_diagram}")

            # Agent 1.5: DNA Classifier
            dna_data = classify_scene_dna(
                content_chunk=content_chunk,
                has_diagram=has_diagram,
                diagram_type="diagram_spatial" if has_diagram else "none"
            )

            log_info(f"[V13 Scene {i+1}] Classified as {dna_data['dna_type']} | has_diagram={has_diagram}")

            # Look up Agent 2's pedagogy strategy for this topic
            strategies = pedagogy_plan.get("teaching_strategies", [])
            strategy = strategies[i] if i < len(strategies) else {}
            explanation_strategy = strategy.get("explanation_strategy", "first_principles")
            narrative_tone = strategy.get("narrative_tone", "storyteller")
            aha_trigger = strategy.get("aha_moment_trigger", "")
            pacing = strategy.get("pacing_note", "normal")

            # Rebuild Agent 3 Prompt dynamically based on DNA classification
            dna_type = dna_data.get("suggested_dna", dna_data.get("dna_type", "CONCEPT_DEFINITION"))
            clean_dna_type = dna_type
            if " " in clean_dna_type:
                clean_dna_type = clean_dna_type.split(" ", 1)[1]
            elif "-" in clean_dna_type:
                clean_dna_type = clean_dna_type.split("-", 1)[1]

            hook_options = OPENING_HOOK_INVENTORY.get(clean_dna_type, OPENING_HOOK_INVENTORY["CONCEPT_DEFINITION"])

            # ── V16 UPGRADE: A-G Opener Style Rotation ──────────────────
            # 7 named opening styles, cycled deterministically per scene.
            # Guarantees no two consecutive scenes share the same style.
            # Style A=Question, B=Historical/Origin, C=Strip-Jargon,
            # D=Textbook-Contrast, E=Scenario/Picture-this, F=Paradox/Surprising,
            # G=Challenge/Most-people
            OPENER_STYLE_ORDER = ['A', 'B', 'C', 'D', 'E', 'F', 'G']
            
            # Map each hook to a style by keywords in its text
            def _classify_hook_style(hook_text: str) -> str:
                h = hook_text.lower()
                if 'question' in h or '?' in h or 'asked' in h:
                    return 'A'
                elif 'before' in h and ('year' in h or '{year}' in hook_text or 'nobody' in h):
                    return 'B'
                elif 'strip' in h or 'jargon' in h or 'forget' in h or 'reduce' in h:
                    return 'C'
                elif 'textbook' in h or 'definition' in h or 'memorize' in h:
                    return 'D'
                elif 'picture' in h or 'scenario' in h or 'imagine' in h or 'think of' in h:
                    return 'E'
                elif 'surprise' in h or 'nobody' in h or 'hidden' in h or 'not' in h.split('.')[0]:
                    return 'F'
                elif 'most' in h or 'common' in h or 'mistake' in h or 'challenge' in h:
                    return 'G'
                else:
                    return random.choice(OPENER_STYLE_ORDER)
            
            # Determine which style to use for this scene (deterministic rotation)
            scene_style_idx = getattr(self, '_opener_style_counter', 0)
            target_style = OPENER_STYLE_ORDER[scene_style_idx % len(OPENER_STYLE_ORDER)]
            self._opener_style_counter = scene_style_idx + 1
            
            # Group hooks by style
            style_hooks = {}
            for h in hook_options:
                s = _classify_hook_style(h)
                style_hooks.setdefault(s, []).append(h)
            
            # Pick from target style, fall back to any unused hook
            used_hooks = getattr(self, '_used_hooks', set())
            candidates = [h for h in style_hooks.get(target_style, []) if h not in used_hooks]
            if not candidates:
                # Fallback: pick any unused hook from this DNA type
                candidates = [h for h in hook_options if h not in used_hooks]
            if not candidates:
                candidates = hook_options  # full reset if all exhausted
            
            selected_hook = candidates[0]  # deterministic: always pick first available
            
            # Format year placeholder if present
            if "{year}" in selected_hook:
                selected_hook = selected_hook.format(year=random.choice([1950, 1970, 1980, 1990, 2000]))
                
            used_hooks.add(selected_hook)
            self._used_hooks = used_hooks

            teaching_unit = {
                "topic": topic_name,
                "core_concept": strategy.get("core_concept", topic_name) or topic_name,
                "teaching_hook": aha_trigger,
                "difficulty": pacing,
                "suggested_dna": clean_dna_type,
                "diagram_paths": [diagram_path] if has_diagram else [],
                "formula_paths": [],
                "table_data": None,
                # ── V16: Scene mode + diagram metadata from Agent 1 ──
                "scene_mode": _scene_mode,
                "diagram_type": _agent1_unit.get("diagram_type", "none") if _agent1_unit else "none",
                "diagram_description": _agent1_unit.get("diagram_description", "") if _agent1_unit else "",
                "diagram_step_sequence": _agent1_unit.get("diagram_step_sequence", []) if _agent1_unit else [],
                "has_insertions": _agent1_unit.get("has_insertions", False) if _agent1_unit else False,
                "has_deletions": _agent1_unit.get("has_deletions", False) if _agent1_unit else False,
                "has_edge_weights": _agent1_unit.get("has_edge_weights", False) if _agent1_unit else False,
            }

            diagram_context = ""
            if has_diagram and diagram_spatial_data and diagram_path in diagram_spatial_data:
                spatial_info = diagram_spatial_data[diagram_path]
                if isinstance(spatial_info, dict):
                    visual_info = spatial_info.get("visual", spatial_info)
                    regions = visual_info.get("regions", []) or visual_info.get("components", []) or visual_info.get("elements", [])
                    connectors = visual_info.get("connectors", [])
                    insights = spatial_info.get("insights", [])
                    
                    diagram_context = "\n═══════════════════════════════════════════════\nDIAGRAM VISUAL COMPONENTS & FLOWS (VLM Analyzed)\n═══════════════════════════════════════════════\n"
                    diagram_context += "The diagram image on screen contains the following exact visual components and connections. You MUST explicitly name and talk about these components and connections in your narration, using their exact labels below as trigger keywords. This is required for downstream visual-event highlighting to work.\n\n"
                    if regions:
                        diagram_context += "Visible Components / Nodes / Regions:\n"
                        for idx, r in enumerate(regions):
                            label = r.get("label", r.get("region_id", ""))
                            desc = r.get("description", r.get("role", ""))
                            diagram_context += f"- Component/Node: \"{label}\" (Role: {desc})\n"
                    if connectors:
                        diagram_context += "\nVisible Connectors / Flows / Arrows:\n"
                        for c in connectors:
                            f_id = c.get("from_region_id") or c.get("from", "")
                            t_id = c.get("to_region_id") or c.get("to", "")
                            lbl = c.get("label", "")
                            wgt = c.get("weight", "")
                            conn_str = f"- Flow/Arrow from \"{f_id}\" to \"{t_id}\""
                            if wgt:
                                conn_str += f" (Weight/Distance: {wgt})"
                            if lbl:
                                conn_str += f" (Label: \"{lbl}\")"
                            diagram_context += conn_str + "\n"
                    if insights:
                        diagram_context += "\nPedagogical Key Insights:\n"
                        for ins in insights:
                            diagram_context += f"- {ins}\n"

                    # V17: Also include VLM-extracted structured node/edge data
                    vlm_nodes = spatial_info.get("diagram_nodes", [])
                    vlm_edges = spatial_info.get("diagram_edges", [])
                    if vlm_nodes:
                        diagram_context += "\nVLM-Extracted Node Labels:\n"
                        for n in vlm_nodes:
                            diagram_context += f"- {n.get('label', '?')} ({n.get('type', 'node')})\n"
                    if vlm_edges:
                        diagram_context += "\nVLM-Extracted Edges with Weights:\n"
                        for e in vlm_edges:
                            edge_str = f"- {e.get('from', '?')} → {e.get('to', '?')}"
                            if e.get('weight'):
                                edge_str += f" (weight={e['weight']})"
                            diagram_context += edge_str + "\n"
                    comp_steps = spatial_info.get("computation_steps", [])
                    if comp_steps:
                        diagram_context += "\nComputation/Algorithm Steps:\n"
                        for si, s in enumerate(comp_steps):
                            diagram_context += f"  Step {si+1}: {s}\n"

            # V16: Also append Agent 1 planned diagram description & step sequence if present
            _tu_diag_desc = teaching_unit.get("diagram_description", "")
            _tu_diag_seq = teaching_unit.get("diagram_step_sequence", [])
            if _tu_diag_desc or _tu_diag_seq:
                diagram_context += "\n═══════════════════════════════════════════════\nPLANNED DIAGRAM & ANIMATION SEQUENCE\n═══════════════════════════════════════════════\n"
                if _tu_diag_desc:
                    diagram_context += f"Diagram Visual Overview: {_tu_diag_desc}\n"
                if _tu_diag_seq:
                    diagram_context += "Chronological Step-by-Step Sequence:\n"
                    for step_idx, step_txt in enumerate(_tu_diag_seq):
                        diagram_context += f"  Step {step_idx+1}: {step_txt}\n"

            system_prompt = AGENT3_QUALITY_RULES + "\n\n" + f"""You are Agent 3 — the Scene Director for an AI-powered educational video platform.

Your job is to write the narration script for ONE lecture scene. This narration will be spoken aloud by a teacher avatar in a video. Every word you write will be heard by a student. Quality and engagement are not optional — they are the entire purpose.

═══════════════════════════════════════════════
SCENE CONTEXT
═══════════════════════════════════════════════
DNA Type: {clean_dna_type}
Topic: {teaching_unit.get('topic', '')}
Core Concept: {teaching_unit.get('core_concept', '')}
Teaching Hook Suggested: {teaching_unit.get('teaching_hook', '')}
Difficulty Level: {teaching_unit.get('difficulty', 'intermediate')}
Source Text (use this as your factual ground truth):
---
{content_chunk}
---
{diagram_context}

═══════════════════════════════════════════════
YOUR MANDATORY OPENING LINE
═══════════════════════════════════════════════
You MUST begin your narration with EXACTLY this opening phrase (copy it word for word, then continue):
"{selected_hook}"

This is not a suggestion. This is a hard requirement. The first words of your narration must match this phrase exactly. Do not paraphrase it. Do not add words before it.

═══════════════════════════════════════════════
NARRATION WRITING RULES — ALL MANDATORY
═══════════════════════════════════════════════

RULE 1 — TEACHER CLASSROOM VOICE: 
Write in a warm, engaging voice of an expert teacher explaining to a class. Do NOT write in a dry textbook, newspaper, or voiceover reading style. Use active interactive prompts: "Look at...", "Notice how...", "Let's trace...", "Observe...", "Here's what happens when...", "Let's break this down step by step...". Guide the student's eyes and thoughts actively.

RULE 2 — FOUR-PART ARC (8 to 12 Sentences Total):
- HOOK (sentences 1-2): Use mandatory opening phrase above + 1 sentence creating curiosity or a real-world scenario.
- EXPLAIN & INTUITION (sentences 3-6): Define core principles, intuitive mental models, analogies, and underlying mechanics using your vast domain knowledge.
- DEMONSTRATE & VISUAL WALKTHROUGH (sentences 7-10): Walk through visual diagrams, equations, or process steps chronologically. Explicitly name visual components and connectors.
- REINFORCE & TAKEAWAY (sentences 11-12): Synthesize into a single memorable takeaway and connect to the broader discipline.

RULE 3 — WORD COUNT REQUIREMENT: 180 TO 260 WORDS.
Deliver a full, rich, professor-level lecture explanation. Never write short summaries or brief 2-3 sentence overviews! Count your words before returning.

RULE 4 — THE GOLD WORD: The field gold_word must be the single most important technical keyword in this scene. It must appear naturally in your narration in a position of emphasis.

RULE 5 — DNA-SPECIFIC VOICE:
- CONCEPT_DEFINITION: Conversational, curious, slightly informal. Use "you" to address the student directly.
- PROCESS_FLOW: Sequential and methodical. Use transition words: "first", "then", "next", "finally", "step" at least twice. One sentence per step.
- CAUSE_EFFECT: Build tension. Name the cause clearly. Use words like "because", "leads to", "results in", "therefore", "causes" at least once. Pause (use a dash —). Then reveal the effect dramatically.
- COMPARISON: Use contrast language: "unlike", "whereas", "difference", "contrast", "compared" at least once. Never describe them in isolation — always compare directly.
- DIAGRAM_SPATIAL: Use spatial language: "on the left", "notice the arrow pointing to", "the component in the center", "this region here". Guide the student's eyes. You MUST explicitly name and talk about the visual components and flows from the DIAGRAM VISUAL COMPONENTS section in the chronological order you explain them.
- WORKED_EXAMPLE: Walk through the formula or example step by step. Name each component before explaining it. Use "this part", "this term", "this value".
- ANALOGY_BRIDGE: Describe the analogy fully first (2-3 sentences). Then explicitly bridge: "This is exactly how [concept] works." Then explain the concept.
- TAKEAWAY_SUMMARY: Short, punchy sentences. Maximum 12 words each. Build to a single memorable conclusion sentence.

RULE 6 — COMBINE SOURCE FACTS WITH LLM DOMAIN KNOWLEDGE:
Use the PDF source text and visual analysis as your anchor, but EXPAND upon it using your vast internal domain knowledge. Explain the underlying "why", real-world applications, mathematical or logical derivations, intuition, and edge cases. Do NOT invent fake data, but DO provide deep, educational domain knowledge.

RULE 7 — NO FILLER PHRASES: Do not use: "In conclusion", "In summary", "As we can see", "It is worth noting", "Importantly", "Essentially", "Basically", "In other words" (as openers), "That being said", "Moving on", "Let us now". These are padding. Remove them.

RULE 8 — HEADING RULES:
- heading_left: 3-6 words, title case, captures the scene's topic as a question or noun phrase. NOT a full sentence.
- heading_right: 2-5 words, subtitle that adds context or the formal name. No punctuation.
- These must be DIFFERENT from each other and must NOT repeat the gold_word in both.

═══════════════════════════════════════════════
OUTPUT FORMAT — RETURN ONLY THIS JSON
═══════════════════════════════════════════════
Return ONLY a valid JSON object. No markdown. No explanation. No text outside the JSON.

{{
  "heading_left": "...",
  "heading_right": "...",
  "gold_word": "...",
  "left_description": "A rich, descriptive paragraph of 5-6 sentences (70-100 words) providing essential conceptual context, real-world applications, and why this topic matters. Written in engaging academic prose.",
  "diagram_description": "If this scene involves a diagram, flow, or visual structure, provide 2-4 sentences describing all elements (nodes, boxes, arrows, connections, layers) and their spatial relationships. Name each component explicitly.",
  "narration": "...",
  "takeaway": "..."
}}

The narration field must be a complete, highly detailed narration script — 180-260 words, starting with the mandatory opening phrase.
The takeaway must be a single sentence of maximum 15 words capturing the scene's lesson.
Do not include bullets in this JSON — they are derived separately.
"""

            user_prompt = f"""You must focus this scene SPECIFICALLY on teaching: "{topic_name}".
Do NOT generate content about other topics. The headings, narration, and takeaway must all be unique to "{topic_name}".

═══ PEDAGOGICAL DIRECTION (from curriculum planner) ═══
- Explanation Strategy: {explanation_strategy}
- Narrative Tone: {narrative_tone}
- Aha Moment to trigger: {aha_trigger}
- Pacing: {pacing}

Content chunk to teach:
\"\"\"{content_chunk[:8000]}\"\"\"

Provide the output matching the schema."""

            # Run Scene Director per scene
            from core.ai_providers import generate_text_json
            prompt = f"{system_prompt}\n\n{user_prompt}"
            try:
                agent3_output = generate_text_json(prompt, task_name=f"agent3_scene_director_scene_{i+1}", max_tokens=3072)
                if not agent3_output or not isinstance(agent3_output, dict):
                    raise ValueError("Empty or invalid JSON returned from unified provider")

                # --- CHANGE 4: Post-Process Agent 3 Output to Derive Bullets ---
                narration_text = agent3_output.get("narration", "")

                # EMPTY-NARRATION GUARD: if the Scene Director's JSON came back
                # truncated/salvaged (e.g. a mid-run model timeout), `narration`
                # can be empty — TTS then skips the scene and the final video
                # loses it entirely. Rather than drop the scene, synthesise a
                # minimal but coherent narration from whatever context we DO
                # have (topic/heading/left_description) so all scenes render.
                if not narration_text or not narration_text.strip():
                    _topic_hint = (
                        agent3_output.get("heading_left")
                        or agent3_output.get("topic")
                        or topic_name
                        or "this concept"
                    )
                    _desc_hint = agent3_output.get("left_description") or ""
                    narration_text = (
                        f"Let's focus on {_topic_hint}. "
                        + (f"{_desc_hint} " if _desc_hint else "")
                        + f"Understanding {_topic_hint} is an important part of this topic, "
                        "and it connects directly to what we have already covered."
                    ).strip()
                    agent3_output["narration"] = narration_text
                    log_error(
                        f"[V13 Scene Director] Scene {valid_scenes_count + 1} had EMPTY narration "
                        f"(likely truncated LLM output) — substituted a minimal fallback narration "
                        f"so the scene still renders."
                    )


                scene_dna = dna_data
                scene_index = valid_scenes_count + 1

                derived_bullets = _derive_bullets_from_narration(narration_text, clean_dna_type)

                # Build final scene Blueprint
                # Generate a smart left_description from Agent3 or derive from narration
                left_desc = agent3_output.get("left_description", "")
                if not left_desc and narration_text:
                    # V16: Auto-derive a rich 4-5 line description from narration
                    # Extract sentences 2-5 from narration (skip the opening hook)
                    import re as _re_desc
                    all_sents = [s.strip() for s in _re_desc.split(r'(?<=[.!?])\s+', narration_text) if len(s.strip()) > 15]
                    # Skip first sentence (usually the hook) and take next 3-4
                    middle_sents = all_sents[1:5] if len(all_sents) > 4 else all_sents[1:4] if len(all_sents) > 2 else all_sents[:3]
                    if middle_sents:
                        left_desc = ' '.join(middle_sents)
                        # Ensure it ends properly
                        if not left_desc.endswith(('.', '!', '?')):
                            left_desc = left_desc.rstrip(',;:—-') + '.'
                    else:
                        left_desc = (f"This scene explores the essential foundations of {topic_name}. "
                                     f"Understanding this concept is critical for building deeper knowledge "
                                     f"in the subject. We will examine how it works, why it matters, "
                                     f"and where it applies in real-world scenarios.")

                scene_blueprint = {
                    "scene_id": f"scene_{scene_index:02d}",
                    "scene_type": clean_dna_type.lower(),
                    "scene_dna": scene_dna,
                    "topic": topic_name,
                    "heading_left": agent3_output.get("heading_left", ""),
                    "gold_word": agent3_output.get("gold_word", ""),
                    "left_description": left_desc,
                    "heading_right": agent3_output.get("heading_right", ""),
                    "narration": narration_text,
                    "bullets": derived_bullets,  # ← derived from narration, not LLM-generated separately
                    "takeaway": agent3_output.get("takeaway", ""),
                    "diagram_description": agent3_output.get("diagram_description", "") or teaching_unit.get("diagram_description", ""),
                    "diagram_refs": teaching_unit.get("diagram_paths", []),
                    "formula_refs": teaching_unit.get("formula_paths", []),
                    "table_data": teaching_unit.get("table_data", None),
                    # ── V16: Scene mode + diagram metadata for downstream pipeline ──
                    "scene_mode": teaching_unit.get("scene_mode", "bullets_only"),
                    "diagram_type": teaching_unit.get("diagram_type", "none"),
                    "diagram_step_sequence": teaching_unit.get("diagram_step_sequence", []),
                    "has_insertions": teaching_unit.get("has_insertions", False),
                    "has_deletions": teaching_unit.get("has_deletions", False),
                    "has_edge_weights": teaching_unit.get("has_edge_weights", False),
                }

                # --- Extra Backend Compatibility / Rendering Fields ---
                scene_blueprint["scene_index"] = scene_index
                scene_blueprint["total_scenes"] = total_scenes
                scene_blueprint["diagram_paths"] = [diagram_path] if has_diagram else []

                if has_diagram:
                    scene_blueprint["diagram_refs"] = [diagram_path]
                    if diagram_spatial_data and diagram_path in diagram_spatial_data:
                        spatial_info = diagram_spatial_data[diagram_path]
                        if isinstance(spatial_info, dict) and "visual" in spatial_info:
                            scene_blueprint["diagram_data"] = spatial_info["visual"]
                        else:
                            scene_blueprint["diagram_data"] = spatial_info
                    else:
                        scene_blueprint["diagram_data"] = {}
                        
                    # Force layout preset to a diagram-supporting layout
                    if scene_blueprint["scene_type"] not in ["diagram_spatial", "process_flow"]:
                        scene_blueprint["scene_type"] = "diagram_spatial"
                        if isinstance(scene_blueprint.get("scene_dna"), dict):
                            scene_blueprint["scene_dna"]["layout_preset"] = "diagram_spatial"
                            scene_blueprint["scene_dna"]["dna_type"] = "DNA-5 DIAGRAM_SPATIAL"
                            scene_blueprint["scene_dna"]["narration_style"] = "guided_tour"
                else:
                    scene_blueprint["diagram_refs"] = []
                    scene_blueprint["diagram_data"] = {}

                # Fallback list for zoom keywords
                scene_blueprint["zoom_words"] = [b.get("zoom_word") for b in derived_bullets if b.get("zoom_word")]

                # Enforce DNA-specific data structures for downstream templates
                if clean_dna_type == "WORKED_EXAMPLE":
                    scene_blueprint["equation_data"] = {
                        "latex": agent3_output.get("latex", f"{topic_name}"),
                        "steps": [
                            {"latex": b.get("text", ""), "label": f"Step {idx+1}", "trigger_word": b.get("trigger_word", "")}
                            for idx, b in enumerate(derived_bullets[:4])
                        ],
                        "variables": []
                    }
                elif clean_dna_type == "COMPARISON":
                    rows = []
                    for b in derived_bullets:
                        rows.append([b.get("text", ""), "", ""])
                    scene_blueprint["table_data"] = {
                        "headers": ["Feature", topic_name, "Alternative"],
                        "rows": rows if rows else [["Aspect 1", "Value A", "Value B"]],
                        "focus_sequence": [
                            {"type": "row", "index": idx, "trigger_word": b.get("trigger_word", "")}
                            for idx, b in enumerate(derived_bullets[:4])
                        ]
                    }

                scenes.append(scene_blueprint)
                valid_scenes_count += 1
                log_info(f"[V13 Scene Director] Choreographed scene {valid_scenes_count}/{total_scenes} ({dna_data['dna_type']})")

            except Exception as e:
                log_error(f"[V13 Scene Director] Failed to parse scene {i+1}: {e}")
                # Safe pedagogical fallback
                scenes.append({
                    "scene_id": f"scene_{valid_scenes_count+1:02d}",
                    "scene_index": valid_scenes_count + 1,
                    "total_scenes": total_scenes,
                    "scene_dna": dna_data,
                    "scene_type": dna_data["layout_preset"],
                    "topic": topic_name,
                    "heading_left": f"Let's explore {topic_name}",
                    "gold_word": topic_name.split()[0] if topic_name.split() else "Topic",
                    "left_description": (f"This scene provides a comprehensive exploration of {topic_name}. "
                                         f"Understanding this concept builds a strong foundation for deeper study. "
                                         f"We examine the key principles, practical applications, and the reasoning "
                                         f"behind why this matters in the broader context of the subject."),
                    "heading_right": topic_name,
                    "narration": f"Here is something most students overlook about {topic_name}. It is not just a definition to memorize — it is a concept that connects to everything else in this subject. Think of it like a key that unlocks multiple doors. Once you understand how {topic_name} works at its core, the rest of the material falls into place naturally.",
                    "takeaway": f"Mastering {topic_name} is the foundation for deeper understanding.",
                    "bullets": [
                        {"num": "01", "text": f"{topic_name} connects to everything else in this subject.", "zoom_word": topic_name.split()[0].lower() if topic_name.split() else "concept", "trigger_word": "overlook", "entrance": "slide_left"}
                    ],
                    "diagram_refs": [diagram_path] if has_diagram else [],
                    "diagram_paths": [diagram_path] if has_diagram else [],
                    "diagram_data": diagram_spatial_data[diagram_path]["visual"] if (has_diagram and diagram_spatial_data and diagram_path in diagram_spatial_data and isinstance(diagram_spatial_data[diagram_path], dict) and "visual" in diagram_spatial_data[diagram_path]) else (diagram_spatial_data[diagram_path] if (has_diagram and diagram_spatial_data and diagram_path in diagram_spatial_data) else {}),
                    "diagram_trigger_word": "examine",
                    "zoom_words": ["element"]
                })
                valid_scenes_count += 1

        return {"scenes": scenes}

    # ──────────────────────────────────────────────────────────────────────
    # Full 3.5-Agent Pipeline
    # ──────────────────────────────────────────────────────────────────────

    def generate_blueprint_v5(
        self,
        document_text: str,
        extracted_images: List[str] = None,
        vlm_pages: List[Dict] = None,
        diagram_spatial_data: Dict = None,
    ) -> Dict:
        """
        Runs the full pipeline:
        Agent 1 (Content Analyst) -> Agent 2 (Pedagogical Planner) -> Agent 3 (DNA Scene Director)
        """
        # Store vlm_pages for passing to direct_scenes
        self._vlm_pages = vlm_pages
        log_info("=" * 60)
        log_info("[V15] Pedagogical Engine — DNA-Aware Pipeline Starting")
        log_info("=" * 60)

        # Agent 1: Analyze content
        content_analysis = self.analyze_content(document_text, vlm_pages)
        if not content_analysis or not any(content_analysis.values()):
            log_error("[V13] Content Analyst returned empty analysis.")
            return None

        # Agent 2: Plan pedagogy
        pedagogy_plan = self.plan_pedagogy(content_analysis, document_text)
        if not pedagogy_plan or not any(pedagogy_plan.values()):
            log_error("[V13] Pedagogical Planner returned empty plan.")
            return None

        # Agent 3: DNA-Aware Scene Director
        blueprint = self.direct_scenes(
            pedagogy_plan=pedagogy_plan,
            content_analysis=content_analysis,
            document_text=document_text,
            extracted_images=extracted_images,
            diagram_spatial_data=diagram_spatial_data,
            vlm_pages=vlm_pages,
        )

        if not blueprint.get("scenes"):
            log_error("[V13] Scene Director returned no scenes.")
            return None

        # Call post-generation diversity validator
        blueprint["scenes"] = _validate_script_diversity(blueprint["scenes"])

        # Add engine tag
        for scene in blueprint.get("scenes", []):
            scene["_pedagogical_engine"] = "v13_3.5agent_dna"

        log_info(f"[V13] Pipeline Complete: {len(blueprint.get('scenes', []))} DNA-grounded scenes created")
        return blueprint

    @staticmethod
    def _extract_json(raw: str) -> Dict:
        """Robust JSON extraction supporting markdown blocks."""
        if raw.startswith("ERROR:"):
            raise ValueError(f"LLM API Error: {raw}")
            
        start_idx = raw.find('{')
        if start_idx == -1:
            raise ValueError("No JSON object found in response")

        bracket_count = 0
        end_idx = -1
        for i in range(start_idx, len(raw)):
            if raw[i] == '{':
                bracket_count += 1
            elif raw[i] == '}':
                bracket_count -= 1
                if bracket_count == 0:
                    end_idx = i + 1
                    break

        if end_idx == -1:
            raise ValueError("Incomplete JSON — LLM truncated response")

        return json.loads(raw[start_idx:end_idx])
