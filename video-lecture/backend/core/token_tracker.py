# -*- coding: utf-8 -*-
"""
SmartStudyInstructor — Token Budget Tracker
Lightweight, file-backed daily token usage tracker per AI provider/model.
Resets automatically at midnight UTC.
"""

import os
import json
import time
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

log = logging.getLogger("token_tracker")

# Daily Token Limits (configurable via environment or defaults)
# NOTE: 90k was FAR too low — a single 9-scene run burns ~90k on scene-director
# calls alone, which caused Groq to be preemptively bypassed mid-run (every
# diagram then fell through to weak OpenRouter models → unparseable JSON → empty
# diagrams). Groq's free tier is per-MINUTE token limited, not a hard 90k/day
# cap, so this daily ceiling is a soft guard only. Raised to a realistic value
# and overridable via .env (GROQ_DAILY_TOKEN_LIMIT).
GROQ_DAILY_TOKEN_LIMIT = int(os.getenv("GROQ_DAILY_TOKEN_LIMIT", "1000000"))  # 1M soft daily guard

GROQ_TPM_INSTANT_LIMIT = int(os.getenv("GROQ_TPM_INSTANT_LIMIT", "5000"))   # 5k safety limit (6k hard limit)
OPENROUTER_DAILY_TOKEN_LIMIT = int(os.getenv("OPENROUTER_DAILY_TOKEN_LIMIT", "500000"))

CACHE_DIR = Path("static/uploads")
BUDGET_FILE = CACHE_DIR / "token_budget.json"


class TokenBudgetTracker:
    def __init__(self, budget_file: Path = BUDGET_FILE):
        self.budget_file = budget_file
        self.budget_file.parent.mkdir(parents=True, exist_ok=True)
        self._load()

    def _get_today_str(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _load(self):
        today = self._get_today_str()
        if self.budget_file.exists():
            try:
                with open(self.budget_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("date") == today:
                    self.data = data
                    return
            except Exception as e:
                log.warning(f"[TokenTracker] Failed to load budget file: {e}")

        # Initialize fresh daily record
        self.data = {
            "date": today,
            "groq_daily_tokens": 0,
            "openrouter_daily_tokens": 0,
            "gemini_daily_tokens": 0,
            "last_updated": time.time()
        }
        self._save()

    def _save(self):
        try:
            self.data["last_updated"] = time.time()
            with open(self.budget_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            log.warning(f"[TokenTracker] Failed to save budget file: {e}")

    def get_groq_remaining_daily_tokens(self) -> int:
        self._load()
        used = self.data.get("groq_daily_tokens", 0)
        return max(0, GROQ_DAILY_TOKEN_LIMIT - used)

    def can_use_groq(self, estimated_tokens: int = 4000) -> bool:
        remaining = self.get_groq_remaining_daily_tokens()
        return remaining >= estimated_tokens

    def get_openrouter_remaining_daily_tokens(self) -> int:
        self._load()
        used = self.data.get("openrouter_daily_tokens", 0)
        return max(0, OPENROUTER_DAILY_TOKEN_LIMIT - used)

    def can_use_openrouter(self, estimated_tokens: int = 4000) -> bool:
        return self.get_openrouter_remaining_daily_tokens() >= estimated_tokens

    def record_usage(self, provider: str, tokens: int):
        self._load()
        provider_key = f"{provider.lower()}_daily_tokens"
        if provider_key in self.data:
            self.data[provider_key] += tokens
        else:
            self.data[provider_key] = tokens
        self._save()

        log.info(f"[TokenTracker] Recorded {tokens} tokens for {provider}. Groq today: {self.data.get('groq_daily_tokens', 0)}/{GROQ_DAILY_TOKEN_LIMIT}")


# Singleton instance
token_tracker = TokenBudgetTracker()
