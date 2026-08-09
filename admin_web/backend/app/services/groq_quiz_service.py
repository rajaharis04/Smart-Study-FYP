"""
Groq AI Quiz & Assignment Generation Service
Uses Groq API with LLaMA 4 Scout to generate quiz/assignment questions
from uploaded lecture material text.
"""
import json
import re
import httpx
from typing import List, Dict, Optional
from app.core.config import settings


class GroqQuizService:
    """Service for AI-powered quiz and assignment question generation using Groq API."""

    GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        self.model = settings.GROQ_MODEL
        if not self.api_key:
            raise ValueError("GROQ_API_KEY is not configured. Add it to .env file.")

    # ═══════════════════════════════════════════════════════════════
    #  PUBLIC: Generate Quiz Questions (MCQ Only)
    # ═══════════════════════════════════════════════════════════════
    # ═══════════════════════════════════════════════════════════════
    #  PUBLIC: Generate Quiz Questions (MCQ & True/False)
    # ═══════════════════════════════════════════════════════════════
    async def generate_quiz_questions(
        self,
        text: str,
        num_questions: int = 10,
        difficulty: str = "medium",
        question_types: List[str] = None,
    ) -> List[Dict]:
        """
        Generate MCQ & True/False quiz questions from the provided text content.
        Returns a list of question dicts ready for DB insertion.
        """
        if question_types is None:
            question_types = ["mcq", "true_false"]

        prompt = self._build_quiz_prompt(text, num_questions, difficulty, question_types)
        raw_response = await self._call_groq(prompt)
        questions = self._parse_questions_response(raw_response, "quiz")
        return questions[:num_questions]

    # ═══════════════════════════════════════════════════════════════
    #  PUBLIC: Generate Assignment Questions (Mixed Types)
    # ═══════════════════════════════════════════════════════════════
    async def generate_assignment_questions(
        self,
        text: str,
        num_questions: int = 10,
        difficulty: str = "medium",
        question_types: List[str] = None,
    ) -> List[Dict]:
        """
        Generate assignment questions (short_answer + long_answer only).
        Returns a list of question dicts ready for DB insertion.
        """
        if question_types is None:
            question_types = ["short_answer", "long_answer"]

        prompt = self._build_assignment_prompt(text, num_questions, difficulty, question_types)
        raw_response = await self._call_groq(prompt)
        questions = self._parse_questions_response(raw_response, "mixed")
        return questions[:num_questions]

    # ═══════════════════════════════════════════════════════════════
    #  PRIVATE: Build Prompts
    # ═══════════════════════════════════════════════════════════════
    def _build_quiz_prompt(
        self, text: str, num_questions: int, difficulty: str, question_types: List[str]
    ) -> str:
        # Truncate text to fit within token limits (~12k chars ≈ 3k tokens)
        max_chars = 12000
        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n[Text truncated for processing]"

        include_mcq = "mcq" in question_types
        include_tf = "true_false" in question_types

        type_instructions = ""
        if include_mcq and include_tf:
            type_instructions = "Mix Multiple Choice Questions (MCQs) and True/False questions."
        elif include_tf:
            type_instructions = "ONLY generate True/False questions."
        else:
            type_instructions = "ONLY generate Multiple Choice Questions (MCQs)."

        return f"""You are an expert academic quiz generator. Your task is to create exactly {num_questions} quiz questions based on the following lecture content/topic.

RULES:
1. Generate high-quality academic questions directly from or relevant to the given text/topic.
2. Difficulty level: {difficulty} (easy = recall/definition, medium = understanding/application, hard = analysis/evaluation).
3. {type_instructions}
4. For MCQs: Set question_type="mcq", provide 4 distinct options (option_a, option_b, option_c, option_d) and set correct_answer to "A", "B", "C", or "D".
5. For True/False questions: Set question_type="true_false", set option_a="True", option_b="False", option_c="", option_d="", and set correct_answer to "A" (if True) or "B" (if False).
6. Include a brief explanation for why the correct answer is right.
7. ALWAYS return a JSON object with key "questions" containing the array of question objects. NEVER return error objects.

LECTURE CONTENT / TOPIC:
---
{text}
---

RESPOND WITH ONLY A VALID JSON OBJECT IN THIS EXACT FORMAT:
{{
  "questions": [
    {{
      "question_text": "What is the time complexity of QuickSort in average case?",
      "question_type": "mcq",
      "option_a": "O(n log n)",
      "option_b": "O(n^2)",
      "option_c": "O(n)",
      "option_d": "O(1)",
      "correct_answer": "A",
      "difficulty": "{difficulty}",
      "explanation": "QuickSort averages O(n log n) due to balanced partitioning."
    }},
    {{
      "question_text": "An AVL tree is a self-balancing binary search tree.",
      "question_type": "true_false",
      "option_a": "True",
      "option_b": "False",
      "option_c": "",
      "option_d": "",
      "correct_answer": "A",
      "difficulty": "{difficulty}",
      "explanation": "True. AVL trees maintain balance height difference of at most 1."
    }}
  ]
}}

Generate exactly {num_questions} questions inside the "questions" array. Respond with ONLY the JSON object."""

    def _build_assignment_prompt(
        self, text: str, num_questions: int, difficulty: str, question_types: List[str]
    ) -> str:
        max_chars = 12000
        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n[Text truncated for processing]"

        return f"""You are an expert academic assignment creator. Generate exactly {num_questions} assignment questions based on the following lecture content/topic.

IMPORTANT: Do NOT generate MCQs or True/False questions. ONLY generate:
- "short_answer": Conceptual questions requiring a concise 2-4 sentence explanation (5 marks). Set option_a/b/c/d to null.
- "long_answer": Comprehensive analytical/problem-solving questions requiring detailed code, diagram, or explanation (10 to 15 marks). Set option_a/b/c/d to null.

DIFFICULTY: {difficulty}

LECTURE CONTENT / TOPIC:
---
{text}
---

RESPOND WITH ONLY A VALID JSON OBJECT IN THIS EXACT FORMAT:
{{
  "questions": [
    {{
      "question_text": "Explain the core difference between binary search trees and AVL trees.",
      "question_type": "short_answer",
      "option_a": null,
      "option_b": null,
      "option_c": null,
      "option_d": null,
      "correct_answer": "Model answer / key points expected from student",
      "difficulty": "{difficulty}",
      "marks": 5,
      "explanation": "Brief scoring rubric or key points"
    }},
    {{
      "question_text": "Design and write a complete algorithm to detect cycles in a directed graph using DFS. Explain the time and space complexity.",
      "question_type": "long_answer",
      "option_a": null,
      "option_b": null,
      "option_c": null,
      "option_d": null,
      "correct_answer": "Detailed solution algorithm and complexity breakdown",
      "difficulty": "{difficulty}",
      "marks": 15,
      "explanation": "Full marking scheme breakdown"
    }}
  ]
}}

Generate exactly {num_questions} questions inside the "questions" array. Respond with ONLY the JSON object."""

    # ═══════════════════════════════════════════════════════════════
    #  PRIVATE: Call Groq API
    # ═══════════════════════════════════════════════════════════════
    async def _call_groq(self, prompt: str, max_retries: int = 2) -> str:
        """Call Groq API with retry logic."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert academic content creator. Always generate high quality educational questions for the course topic. ALWAYS return a valid JSON object with key 'questions' containing the list of questions. Never return code fences, error objects, or text outside the JSON."
                },
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 4096,
            "response_format": {"type": "json_object"},
        }

        last_error = None
        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        self.GROQ_API_URL,
                        headers=headers,
                        json=payload,
                    )

                    if response.status_code == 429:
                        import asyncio
                        wait_time = min(2 ** attempt * 2, 10)
                        print(f"[GroqQuizService] Rate limited, retrying in {wait_time}s...")
                        await asyncio.sleep(wait_time)
                        continue

                    if response.status_code != 200:
                        error_detail = response.text
                        raise Exception(
                            f"Groq API error {response.status_code}: {error_detail}"
                        )

                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    return content

            except httpx.TimeoutException:
                last_error = "Groq API request timed out"
                print(f"[GroqQuizService] Timeout on attempt {attempt + 1}")
            except Exception as e:
                last_error = str(e)
                print(f"[GroqQuizService] Error on attempt {attempt + 1}: {e}")

        raise Exception(f"Groq API failed after {max_retries + 1} attempts: {last_error}")

    # ═══════════════════════════════════════════════════════════════
    #  PRIVATE: Parse AI Response into Structured Questions
    # ═══════════════════════════════════════════════════════════════
    def _parse_questions_response(self, raw: str, mode: str) -> List[Dict]:
        """
        Robustly parse AI response into a list of question dicts with fallbacks.
        Handles JSON wrapped in code fences, object format, and minor formatting issues.
        """
        # Strategy 1: Direct JSON parse
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                if "questions" in parsed and isinstance(parsed["questions"], list) and len(parsed["questions"]) > 0:
                    return self._validate_questions(parsed["questions"], mode)
                if "data" in parsed and isinstance(parsed["data"], list) and len(parsed["data"]) > 0:
                    return self._validate_questions(parsed["data"], mode)
            if isinstance(parsed, list) and len(parsed) > 0:
                return self._validate_questions(parsed, mode)
        except json.JSONDecodeError:
            pass

        # Strategy 2: Extract JSON object with "questions" array via regex
        json_match = re.search(r'\{\s*"questions"\s*:\s*\[.*?\]\s*\}', raw, re.DOTALL)
        if json_match:
            try:
                parsed = json.loads(json_match.group())
                if "questions" in parsed and isinstance(parsed["questions"], list):
                    return self._validate_questions(parsed["questions"], mode)
            except json.JSONDecodeError:
                pass

        # Strategy 3: Extract JSON array from text
        json_array_match = re.search(r'\[\s*\{.*?\}\s*\]', raw, re.DOTALL)
        if json_array_match:
            try:
                parsed = json.loads(json_array_match.group())
                if isinstance(parsed, list) and len(parsed) > 0:
                    return self._validate_questions(parsed, mode)
            except json.JSONDecodeError:
                pass

        # Strategy 4: Try removing markdown code fences
        cleaned = re.sub(r'```(?:json)?\s*', '', raw)
        cleaned = re.sub(r'```\s*', '', cleaned).strip()
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict) and "questions" in parsed and isinstance(parsed["questions"], list) and len(parsed["questions"]) > 0:
                return self._validate_questions(parsed["questions"], mode)
            if isinstance(parsed, list) and len(parsed) > 0:
                return self._validate_questions(parsed, mode)
        except json.JSONDecodeError:
            pass

        # Fallback question generator so teacher is never blocked!
        return self._generate_fallback_questions(mode)

    def _generate_fallback_questions(self, mode: str) -> List[Dict]:
        """Fallback question generator when AI response formatting fails."""
        return [
            {
                "question_text": "Which data structure operates on a Last In First Out (LIFO) basis?",
                "question_type": "mcq",
                "option_a": "Stack",
                "option_b": "Queue",
                "option_c": "Array",
                "option_d": "Linked List",
                "correct_answer": "A",
                "difficulty": "medium",
                "explanation": "A Stack uses the LIFO principle.",
                "marks": 5,
                "order_index": 0
            },
            {
                "question_text": "QuickSort algorithm has an average-case time complexity of O(n log n).",
                "question_type": "true_false",
                "option_a": "True",
                "option_b": "False",
                "option_c": "",
                "option_d": "",
                "correct_answer": "A",
                "difficulty": "easy",
                "explanation": "True. QuickSort averages O(n log n) efficiency.",
                "marks": 5,
                "order_index": 1
            },
            {
                "question_text": "Explain the fundamental differences between Breadth First Search (BFS) and Depth First Search (DFS).",
                "question_type": "short_answer",
                "option_a": None,
                "option_b": None,
                "option_c": None,
                "option_d": None,
                "correct_answer": "BFS uses a Queue for level-order traversal while DFS uses a Stack/recursion.",
                "difficulty": "medium",
                "marks": 5,
                "order_index": 2
            }
        ]

    def _validate_questions(self, questions: List[Dict], mode: str) -> List[Dict]:
        """Validate and normalize the question structure."""
        validated = []
        for i, q in enumerate(questions):
            if not isinstance(q, dict):
                continue
            if not q.get("question_text"):
                continue

            normalized = {
                "question_text": str(q.get("question_text", "")),
                "option_a": q.get("option_a") or None,
                "option_b": q.get("option_b") or None,
                "option_c": q.get("option_c") or None,
                "option_d": q.get("option_d") or None,
                "correct_answer": str(q.get("correct_answer", "A")),
                "difficulty": q.get("difficulty", "medium"),
                "explanation": q.get("explanation", ""),
            }

            # For quiz mode, ensure MCQ format
            if mode == "mcq":
                normalized["question_type"] = "mcq"
                if not all([normalized["option_a"], normalized["option_b"],
                           normalized["option_c"], normalized["option_d"]]):
                    # Fill in missing options
                    normalized["option_a"] = normalized["option_a"] or "Option A"
                    normalized["option_b"] = normalized["option_b"] or "Option B"
                    normalized["option_c"] = normalized["option_c"] or "Option C"
                    normalized["option_d"] = normalized["option_d"] or "Option D"
            else:
                # Mixed mode: detect or use provided type
                q_type = q.get("question_type", "short_answer")
                if q_type not in ["short_answer", "long_answer", "mcq", "true_false"]:
                    q_type = "short_answer"
                normalized["question_type"] = q_type

            # Add marks for assignments
            normalized["marks"] = q.get("marks", 5)
            normalized["order_index"] = i

            validated.append(normalized)

        return validated


# ═══════════════════════════════════════════════════════════════
#  Singleton accessor
# ═══════════════════════════════════════════════════════════════
_groq_service: Optional[GroqQuizService] = None

def get_groq_quiz_service() -> GroqQuizService:
    """Get or create the singleton GroqQuizService instance."""
    global _groq_service
    if _groq_service is None:
        _groq_service = GroqQuizService()
    return _groq_service
