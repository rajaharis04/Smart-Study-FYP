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
    async def generate_quiz_questions(
        self,
        text: str,
        num_questions: int = 10,
        difficulty: str = "medium",
    ) -> List[Dict]:
        """
        Generate MCQ quiz questions from the provided text content.
        Returns a list of question dicts ready for DB insertion.
        """
        prompt = self._build_quiz_prompt(text, num_questions, difficulty)
        raw_response = await self._call_groq(prompt)
        questions = self._parse_questions_response(raw_response, "mcq")
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
    def _build_quiz_prompt(self, text: str, num_questions: int, difficulty: str) -> str:
        # Truncate text to fit within token limits (~12k chars ≈ 3k tokens)
        max_chars = 12000
        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n[Text truncated for processing]"

        return f"""You are an expert academic quiz generator. Your task is to create exactly {num_questions} multiple-choice questions (MCQs) based STRICTLY on the following lecture content.

RULES:
1. Each question must be directly answerable from the given text content.
2. Difficulty level: {difficulty} (easy = recall/definition, medium = understanding/application, hard = analysis/evaluation).
3. Each question must have exactly 4 options (A, B, C, D) with exactly one correct answer.
4. Options should be plausible and well-crafted — avoid obviously wrong distractors.
5. Include a brief explanation for why the correct answer is right.

LECTURE CONTENT:
---
{text}
---

RESPOND WITH ONLY a valid JSON array. No markdown, no explanation, no preamble. Just the JSON array:
[
  {{
    "question_text": "What is ...?",
    "option_a": "First option",
    "option_b": "Second option",
    "option_c": "Third option",
    "option_d": "Fourth option",
    "correct_answer": "A",
    "difficulty": "{difficulty}",
    "explanation": "Brief explanation of the correct answer"
  }}
]

Generate exactly {num_questions} questions. Respond with ONLY the JSON array."""

    def _build_assignment_prompt(
        self, text: str, num_questions: int, difficulty: str, question_types: List[str]
    ) -> str:
        max_chars = 12000
        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n[Text truncated for processing]"

        return f"""You are an expert academic assignment creator. Generate exactly {num_questions} assignment questions based on the following lecture content.

IMPORTANT: Do NOT generate MCQs or True/False questions. ONLY generate:
- "short_answer": Conceptual questions requiring a concise 2-4 sentence explanation (5 marks). Set option_a/b/c/d to null.
- "long_answer": Comprehensive analytical/problem-solving questions requiring detailed code, diagram, or explanation (10 to 15 marks). Set option_a/b/c/d to null.

DIFFICULTY: {difficulty}

LECTURE CONTENT:
---
{text}
---

RESPOND WITH ONLY a valid JSON array. No markdown, no explanation:
[
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

Generate exactly {num_questions} questions. Respond with ONLY the JSON array."""

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
                    "content": "You are an expert academic content creator. Always respond with valid JSON arrays only. Never include markdown formatting, code fences, or explanatory text outside the JSON."
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
                        # Rate limited — wait and retry
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
        Robustly parse AI response into a list of question dicts.
        Handles JSON wrapped in code fences, extra text, and minor formatting issues.
        """
        # Strategy 1: Direct JSON parse
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return self._validate_questions(parsed, mode)
            if isinstance(parsed, dict):
                if "questions" in parsed and isinstance(parsed["questions"], list):
                    return self._validate_questions(parsed["questions"], mode)
                if all(isinstance(v, dict) for v in parsed.values()):
                    return self._validate_questions(list(parsed.values()), mode)
        except json.JSONDecodeError:
            pass

        # Strategy 2: Extract JSON array from text (handles markdown code fences)
        json_match = re.search(r'\[\s*\{.*?\}\s*\]', raw, re.DOTALL)
        if json_match:
            try:
                parsed = json.loads(json_match.group())
                return self._validate_questions(parsed, mode)
            except json.JSONDecodeError:
                pass

        # Strategy 3: Try removing markdown code fences
        cleaned = re.sub(r'```(?:json)?\s*', '', raw)
        cleaned = re.sub(r'```\s*', '', cleaned).strip()
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, list):
                return self._validate_questions(parsed, mode)
            if isinstance(parsed, dict) and "questions" in parsed:
                return self._validate_questions(parsed["questions"], mode)
        except json.JSONDecodeError:
            pass

        raise Exception(f"Failed to parse AI response as valid question JSON. Raw response: {raw[:500]}")

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
