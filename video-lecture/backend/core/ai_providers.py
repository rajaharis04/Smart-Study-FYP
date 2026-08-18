"""
ai_providers.py — Unified AI provider router for SmartStudyInstructor.

FULL FREE-MODEL ROUTING STRATEGY (2026-07-29, ALL IDs LIVE-VERIFIED):
─────────────────────────────────────────────────────────────────────────────
TEXT TASKS (JSON generation, narration, analysis):
  Groq PRIMARY chain (Groq-priority, strongest-first, 3-key pool):
    Tier 1a: Groq  llama-3.3-70b-versatile   ← fast, reliable JSON (json_mode)
    Tier 1b: Groq  openai/gpt-oss-120b        ← 120B reasoning backup (prompt-json)
    Tier 1c: Groq  openai/gpt-oss-20b         ← 20B fast reasoning
    Tier 1d: Groq  llama-3.1-8b-instant       ← high-throughput small tasks

  OpenRouter FREE fallback chain (after Groq exhausted):
    Tier 2a: nvidia/nemotron-3-ultra-550b-a55b:free  ← 550B, strongest free
    Tier 2b: nvidia/nemotron-3-super-120b-a12b:free  ← strong 120B reasoner
    Tier 2c: openai/gpt-oss-20b:free                 ← clean JSON, no preamble

  Tier 3:  Gemini API  gemini-2.0-flash  ← last resort (own key)

VISION TASKS (diagram/page image analysis):
  Tier 1:  OpenRouter  qwen/qwen3-vl-32b-instruct       ← best diagram spatial
  Tier 2:  OpenRouter  qwen/qwen3-vl-8b-instruct         ← faster fallback
  Tier 2b: OpenRouter  nvidia/nemotron-nano-12b-v2-vl:free ← FREE multimodal
  Tier 3:  Gemini API  gemini-2.0-flash                  ← last resort

PREMIUM ROUTING (Agent1 content analysis + Agent2 pedagogy):
  gpt-oss-120b (Groq) → llama-3.3-70b (Groq) → nemotron-550b:free → fallback chain.
  These jobs set the quality ceiling for the whole video.

JSON-MODE WHITELIST:
  Only llama models support response_format=json_object. gpt-oss/nemotron get a
  strong system-prompt instruction instead (fixes 400 JSON-validation errors).
─────────────────────────────────────────────────────────────────────────────
"""


import os
import json
import re
import base64
import time
import logging
from pathlib import Path
from typing import Optional

log = logging.getLogger("ai_providers")

from dotenv import load_dotenv
env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

# ── Lazy Client Setup ───────────────────────────────────────────────────────
# ── Groq API Key Pool Rotation ─────────────────────────────────────────────
_groq_clients: list = []
_current_groq_idx: int = 0

def _get_groq():
    global _groq_clients, _current_groq_idx
    if not _groq_clients:
        from groq import Groq
        raw_keys = os.getenv("GROQ_API_KEYS") or os.getenv("GROQ_API_KEY") or ""
        keys = [k.strip() for k in raw_keys.split(",") if k.strip()]
        if not keys:
            keys = ["dummy_key_to_prevent_init_crash"]
        _groq_clients = [Groq(api_key=k) for k in keys]
        _current_groq_idx = 0
    return _groq_clients[_current_groq_idx % len(_groq_clients)]

def _rotate_groq_key() -> bool:
    global _current_groq_idx, _groq_clients
    if len(_groq_clients) > 1 and _current_groq_idx < len(_groq_clients) - 1:
        _current_groq_idx += 1
        log.warning(f"[ai_providers] Rotated to Groq API Key #{_current_groq_idx + 1} of {len(_groq_clients)}")
        return True
    return False

_openrouter_client = None
def _get_openrouter():
    global _openrouter_client
    if _openrouter_client is None:
        from openai import OpenAI
        api_key = os.getenv("OPENROUTER_API_KEY") or "dummy_key_to_prevent_init_crash"
        _openrouter_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            default_headers={
                "HTTP-Referer": "https://smartstudyinstructor.app",
                "X-Title": "SmartStudyInstructor"
            }
        )
    return _openrouter_client

_gemini_configured = False
_gemini_text_model = None
_gemini_vision_model = None
def _get_gemini():
    global _gemini_configured, _gemini_text_model, _gemini_vision_model
    if not _gemini_configured:
        import google.generativeai as genai
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
        _gemini_text_model = genai.GenerativeModel("gemini-2.0-flash")
        _gemini_vision_model = genai.GenerativeModel("gemini-2.0-flash")
        _gemini_configured = True
    return _gemini_text_model, _gemini_vision_model

# ── LLM Response Cache ──────────────────────────────────────────────────────
CACHE_FILE = Path("static/uploads/llm_cache.json")
CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
_llm_cache_data: dict = {}

def _load_llm_cache():
    global _llm_cache_data
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                _llm_cache_data = json.load(f)
        except Exception:
            _llm_cache_data = {}

def _save_llm_cache():
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(_llm_cache_data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

_load_llm_cache()

def _get_cache_key(task_name: str, prompt: str) -> str:
    import hashlib
    h = hashlib.md5(f"{task_name}:{prompt}".encode("utf-8")).hexdigest()
    return f"{task_name}_{h}"

def _get_cached_response(task_name: str, prompt: str) -> Optional[dict | list | str]:
    key = _get_cache_key(task_name, prompt)
    if key in _llm_cache_data:
        log.info(f"[{task_name}] [Cache] Hit for LLM response key: {key[:16]}...")
        return _llm_cache_data[key]
    return None

def _set_cached_response(task_name: str, prompt: str, data: dict | list | str):
    key = _get_cache_key(task_name, prompt)
    _llm_cache_data[key] = data
    _save_llm_cache()

# ── TEXT MODELS (Groq) ──────────────────────────────────────────────────────
# ALL IDs LIVE-VERIFIED against Groq /models endpoint (2026-07-29). Groq-priority
# (matches original design intent). Strongest-first.
# llama-3.3-70b: fast, reliable, clean JSON — proven workhorse
# gpt-oss-120b: 120B reasoning, strong backup (NO json_object mode → prompt only)
# gpt-oss-20b: 20B, fast reasoning fallback
# llama-3.1-8b: high-throughput small tasks only
# NOTE: kimi-k2 / qwen3-235b are NOT on Groq (404) — removed. They live only on
#       OpenRouter. qwen3.6-27b EXCLUDED — emits <think> blocks that corrupt JSON.
GROQ_TEXT_MODELS = [
    "llama-3.3-70b-versatile",   # Tier 1a: fast, reliable, proven
    "openai/gpt-oss-120b",       # Tier 1b: 120B reasoning backup
    "openai/gpt-oss-20b",        # Tier 1c: 20B fast reasoning
    "llama-3.1-8b-instant",      # Tier 1d: fast small tasks
]

# Models that support response_format=json_object (whitelist).
# gpt-oss models 400 on json_object → they get strong system-prompt instead.
_GROQ_JSON_MODE_SUPPORTED = {
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "llama-3.1-70b-versatile",
}

# ── VISION MODELS (Qwen-VL via OpenRouter) ──────────────────────────────────
# Qwen3-VL: best-in-class diagram/spatial understanding. LIVE-VERIFIED.
QWEN_VL_32B = "qwen/qwen3-vl-32b-instruct"   # primary — best diagram spatial reasoning
QWEN_VL_7B  = "qwen/qwen3-vl-8b-instruct"    # faster fallback
GROQ_VISION_MODELS = []  # Groq vision preview models deleted upstream — disabled

# Vision free fallbacks via OpenRouter (LIVE-VERIFIED 2026-07-29)
# nemotron-nano-vl:free is a genuine FREE multimodal model.
OPENROUTER_VISION_FREE_MODELS = [
    "nvidia/nemotron-nano-12b-v2-vl:free",   # FREE multimodal vision
]

# ── OPENROUTER FREE TEXT MODELS (LIVE-VERIFIED 2026-07-29) ──────────────────
# Intelligence-first fallback chain, all 100% FREE. Tried after Groq exhausted.
# nemotron-3-ultra-550b: strongest free reasoner (user asked nvidia-greatest first)
# nemotron-3-super-120b: strong 120B reasoner
# gpt-oss-20b: clean JSON, no reasoning preamble
# NOTE: qwen3-235b:free and gemini-2.5-flash:free do NOT exist as free tier — removed.
OPENROUTER_FREE_TEXT_MODELS = [
    "nvidia/nemotron-3-ultra-550b-a55b:free",   # 550B — strongest free → primary
    "nvidia/nemotron-3-super-120b-a12b:free",   # strong 120B reasoner
    "openai/gpt-oss-20b:free",                  # clean JSON, no reasoning preamble
]

# Kept for backward-compat with generate_text_raw single-model path.
OPENROUTER_TEXT_MODEL = "nvidia/nemotron-3-super-120b-a12b:free"


# ── PREMIUM (highest-reasoning) TEXT MODELS for Agent1/Agent2 ───────────────
# These jobs (content analysis + pedagogy planning) set the quality ceiling for
# the whole video. gpt-oss-120b leads (strongest Groq reasoner), llama-3.3-70b
# reliable fallback. On Groq miss, delegates to standard router → nemotron-550b.
GROQ_PREMIUM_TEXT_MODELS = [
    "openai/gpt-oss-120b",       # 120B — strongest Groq reasoner
    "llama-3.3-70b-versatile",   # reliable fallback
]



# ── Health tracker ─────────────────────────────────────────────────────────
_provider_failures: dict[str, int] = {
    "groq": 0, "openrouter_text": 0, "openrouter_32b": 0, "openrouter_7b": 0, "gemini": 0
}
_MAX_FAILURES = 3


def _is_healthy(provider: str) -> bool:
    # Instant bypass if keys are missing
    if provider == "groq" and not (os.getenv("GROQ_API_KEY") or os.getenv("GROQ_API_KEYS")):
        return False
    if (provider.startswith("openrouter")) and not os.getenv("OPENROUTER_API_KEY"):
        return False
    if provider == "gemini" and not os.getenv("GEMINI_API_KEY"):
        return False
    return _provider_failures.get(provider, 0) < _MAX_FAILURES


def _mark_failed(provider: str):
    _provider_failures[provider] = _provider_failures.get(provider, 0) + 1
    log.warning(f"[ai_providers] {provider} failure count: {_provider_failures[provider]}")


# ── RETRY-BEFORE-FALLBACK CONFIG ────────────────────────────────────────────
# Root-cause fix: previously ONE Groq 429 dropped the whole request to a weaker
# fallback (→ corrupt script/diagram). We now retry the SAME strong model with
# exponential backoff before ever degrading. Only permanent errors (daily-limit
# TPD, auth, model-not-found) skip retries.
_RETRY_BACKOFFS = [2.0, 4.0, 8.0]   # seconds — 3 retries max per model

# Global pacing throttle: minimum gap between premium Groq calls so a burst of
# scenes doesn't trip the per-minute TPM ceiling (the thing that used to force
# the mid-run Gemini downgrade).
_last_premium_call_ts: float = 0.0
_PREMIUM_MIN_GAP = 1.2   # seconds


def _is_transient_rate_limit(err_str: str) -> bool:
    """A 429/rate-limit that is worth RETRYING (per-minute TPM/RPM), as opposed
    to a permanent per-day (TPD) exhaustion which should trigger key-rotation
    or fallback instead."""
    low = err_str.lower()
    if "429" not in err_str and "rate_limit" not in low and "rate limit" not in low:
        return False
    # Per-DAY exhaustion is NOT transient — don't waste retries on it.
    if "tpd" in low or "tokens per day" in low or "per day" in low:
        return False
    return True


def _pace_premium_call():
    """Throttle consecutive premium calls to stay under TPM burst limits."""
    global _last_premium_call_ts
    now = time.time()
    gap = now - _last_premium_call_ts
    if 0 < gap < _PREMIUM_MIN_GAP:
        time.sleep(_PREMIUM_MIN_GAP - gap)
    _last_premium_call_ts = time.time()


def run_healthcheck() -> dict:
    """Ping every configured provider once and return a status dict. Call this
    at pipeline startup so degraded/dead models are visible BEFORE a run — no
    more silent mid-run downgrades. Safe to call anytime; never raises."""
    status: dict[str, str] = {}
    # Groq
    try:
        _get_groq().chat.completions.create(
            model=GROQ_TEXT_MODELS[0],
            messages=[{"role": "user", "content": "ok"}], max_tokens=3, timeout=15.0)
        status["groq"] = "OK"
    except Exception as e:
        status["groq"] = f"FAIL: {str(e)[:80]}"
    # OpenRouter text (first working free model)
    try:
        _get_openrouter().chat.completions.create(
            model=OPENROUTER_FREE_TEXT_MODELS[0],
            messages=[{"role": "user", "content": "ok"}], max_tokens=3, timeout=20.0)
        status["openrouter_text"] = "OK"
    except Exception as e:
        status["openrouter_text"] = f"FAIL: {str(e)[:80]}"
    # OpenRouter vision
    try:
        _get_openrouter().chat.completions.create(
            model=QWEN_VL_32B,
            messages=[{"role": "user", "content": "ok"}], max_tokens=3, timeout=20.0)
        status["openrouter_vision"] = "OK"
    except Exception as e:
        status["openrouter_vision"] = f"FAIL: {str(e)[:80]}"
    log.info("=" * 60)
    log.info("[ai_providers] STARTUP MODEL HEALTH CHECK")
    for prov, st in status.items():
        emoji = "✅" if st == "OK" else "❌"
        log.info(f"[ai_providers]   {emoji} {prov}: {st}")
    log.info("=" * 60)
    return status



def _close_truncated_json(text: str) -> Optional[dict | list]:
    """
    Best-effort recovery of a TRUNCATED JSON payload (the #1 cause of empty
    diagrams). When an LLM hits max_tokens mid-object, the tail is cut off,
    leaving unbalanced braces/brackets and possibly a dangling string.

    Strategy:
      1. Drop any trailing incomplete token after the last complete value.
      2. Walk the string tracking string-state and bracket depth.
      3. Append the exact closing brackets/braces needed to balance it.
    This preserves every fully-formed node/edge the model DID emit instead of
    throwing the whole diagram away.
    """
    if not text:
        return None
    # Trim to the last structurally meaningful char to avoid a half-written token
    # (e.g. a dangling `"lab` or `12` with no comma). Cut back to the last }, ],
    # ", or digit — the latter handles numbers cut mid-value like `"x":30`.
    last_good = max(
        text.rfind('}'), text.rfind(']'), text.rfind('"'),
        max((i for i, c in enumerate(text) if c.isdigit()), default=-1),
    )
    if last_good == -1:
        return None
    candidate = text[:last_good + 1]


    # Re-scan to compute what still needs closing, respecting strings/escapes.
    stack = []
    in_str = False
    escaped = False
    for ch in candidate:
        if in_str:
            if escaped:
                escaped = False
            elif ch == '\\':
                escaped = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch in '{[':
            stack.append(ch)
        elif ch == '}':
            if stack and stack[-1] == '{':
                stack.pop()
        elif ch == ']':
            if stack and stack[-1] == '[':
                stack.pop()

    if in_str:
        candidate += '"'
    # Remove any trailing comma before we start closing brackets
    candidate = re.sub(r',\s*$', '', candidate.rstrip())
    # Close remaining open containers in LIFO order
    for opener in reversed(stack):
        candidate += '}' if opener == '{' else ']'

    candidate = re.sub(r',\s*([}\]])', r'\1', candidate)
    try:
        return json.loads(candidate)
    except Exception:
        return None


def _repair_json(raw: str) -> Optional[dict | list]:
    """Strip markdown fences, fix trailing commas, extract JSON exhaustively.

    Adds truncation recovery: if the model was cut off by max_tokens, salvage
    every complete element instead of discarding the whole response.
    """
    if not raw:
        return None
    text = raw.strip()
    # Remove Qwen/Deepseek thinking blocks <think>...</think> (both closed and
    # UNCLOSED — an unclosed <think> at truncation would otherwise swallow all).
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    text = re.sub(r'<think>.*$', '', text, flags=re.DOTALL)
    text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'\s*```\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r',\s*([}\]])', r'\1', text)
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        match = re.search(r'(\{.*\}|\[.*\])', text, re.DOTALL)
        if match:
            try:
                candidate = match.group(1).strip()
                candidate = re.sub(r',\s*([}\]])', r'\1', candidate)
                return json.loads(candidate)
            except Exception:
                pass
    # ── Last resort: recover a truncated payload ──────────────────────────
    start = text.find('{')
    if start == -1:
        start = text.find('[')
    if start != -1:
        recovered = _close_truncated_json(text[start:])
        if recovered is not None:
            log.warning("[_repair_json] Recovered TRUNCATED JSON payload "
                        "(response was cut off by token limit — salvaged partial content)")
            return recovered
    return None



def _encode_image(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


# ══════════════════════════════════════════════════════════════════════════
# PUBLIC API — TEXT TASKS
# ══════════════════════════════════════════════════════════════════════════

def generate_text_json(
    prompt: str,
    task_name: str = "text_task",
    max_tokens: int = 2048,
    temperature: float = 0.3,
    use_cache: bool = True
) -> Optional[dict | list]:
    """
    Text-in → JSON-out.
    Routes intelligently:
      1. Checks LLM Cache first if enabled.
      2. Checks TokenBudgetTracker for Groq daily limit BEFORE calling.
      3. Skips Groq preemptively if budget is low, routing directly to OpenRouter or Gemini.
      4. Tracks and logs exact routing reasons.
    """
    from core.token_tracker import token_tracker

    if use_cache:
        cached = _get_cached_response(task_name, prompt)
        if cached is not None and isinstance(cached, (dict, list)):
            return cached

    # Estimate required tokens (prompt chars / 3.5 + max_tokens)
    est_prompt_tokens = (len(prompt) // 3) + max_tokens

    # ── PREEMPTIVE ROUTING CHECK FOR GROQ ─────────────────────────────────
    can_use_groq = _is_healthy("groq") and token_tracker.can_use_groq(est_prompt_tokens)
    rem_groq = token_tracker.get_groq_remaining_daily_tokens()

    if _is_healthy("groq") and not can_use_groq:
        log.warning(
            f"[routing] [{task_name}] PREEMPTIVE BYPASS of Groq: "
            f"Remaining daily budget ({rem_groq}) < estimated request tokens ({est_prompt_tokens}). "
            f"Routing directly to OpenRouter."
        )

    # ── TIER 1: Groq (llama-3.3-70b-versatile) ─────────────────────────────
    if can_use_groq:
        for model_name in GROQ_TEXT_MODELS:
            # If 8b-instant model, enforce TPM limit (skip if prompt too big)
            if "8b-instant" in model_name and est_prompt_tokens > 4500:
                log.info(f"[{task_name}] Skipping Groq ({model_name}): Request too large ({est_prompt_tokens} tokens > 4500 limit)")
                continue

            kwargs = {
                "model": model_name,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a precise JSON generator. Return ONLY valid JSON. No markdown. No explanation. No text outside the JSON structure."
                    },
                    {"role": "user", "content": prompt}
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
                "timeout": 50.0
            }
            # Only use json_object for models that support it (whitelist).
            # Others get strong system-prompt instruction only — avoids 400 errors.
            if model_name in _GROQ_JSON_MODE_SUPPORTED:
                kwargs["response_format"] = {"type": "json_object"}

            # ── RETRY-BEFORE-FALLBACK ─────────────────────────────────────
            # Try this SAME strong model up to len(_RETRY_BACKOFFS)+1 times on a
            # TRANSIENT (per-minute TPM/RPM) 429 before degrading. This is the
            # core fix for mid-run downgrades: a momentary rate blip no longer
            # kicks the request down to a weaker fallback model.
            for attempt in range(len(_RETRY_BACKOFFS) + 1):
                try:
                    log.info(f"[routing] [{task_name}] Tier 1: Groq | SERVED BY MODEL: {model_name} "
                             f"| attempt {attempt + 1} | budget {rem_groq} left")
                    resp = _get_groq().chat.completions.create(**kwargs)
                    raw = resp.choices[0].message.content
                    parsed = _repair_json(raw)

                    usage_tokens = getattr(resp, "usage", None)
                    total_tok = usage_tokens.total_tokens if usage_tokens else est_prompt_tokens
                    token_tracker.record_usage("groq", total_tok)

                    if parsed is not None:
                        log.info(f"[{task_name}] ✅ SERVED BY: Groq/{model_name} ({total_tok} tokens)")
                        _provider_failures["groq"] = 0
                        if use_cache:
                            _set_cached_response(task_name, prompt, parsed)
                        return parsed
                    log.warning(f"[{task_name}] Groq ({model_name}) returned unparseable JSON")
                    break  # unparseable is not a rate issue → next model
                except Exception as e:
                    err_str = str(e)
                    # Permanent per-DAY exhaustion → rotate key or give up on Groq.
                    if ("tpd" in err_str.lower() or "tokens per day" in err_str.lower()
                            or "per day" in err_str.lower()):
                        log.warning(f"[{task_name}] Groq ({model_name}) DAILY limit hit: {err_str[:80]}")
                        if _rotate_groq_key():
                            log.info(f"[{task_name}] Rotated Groq key — retrying same model")
                            continue
                        log.warning(f"[{task_name}] All Groq keys exhausted (TPD). Bypassing Groq.")
                        _mark_failed("groq")
                        break
                    # Transient TPM/RPM 429 → exponential backoff retry SAME model.
                    if _is_transient_rate_limit(err_str) and attempt < len(_RETRY_BACKOFFS):
                        wait = _RETRY_BACKOFFS[attempt]
                        log.warning(f"[{task_name}] Groq ({model_name}) transient 429 — "
                                    f"backoff {wait}s then retry (attempt {attempt + 1})")
                        time.sleep(wait)
                        continue
                    # Any other error → next model.
                    log.warning(f"[{task_name}] Groq error with model {model_name}: {err_str[:120]}")
                    break

            # Only mark Groq failed if we actually TRIED it and all models failed.
            # Do NOT mark failed on budget-skip (can_use_groq was False).
            _mark_failed("groq")


    # ── TIER 2: OpenRouter free model chain ────────────────────────────────
    # Tries deepseek-r1:free → gemini-2.0-flash-exp:free → llama-3.3-70b:free
    # in order. Each model is attempted independently; failure moves to next.
    if _is_healthy("openrouter_text"):
        for or_model in OPENROUTER_FREE_TEXT_MODELS:
            try:
                log.info(f"[routing] [{task_name}] Tier 2: OpenRouter ({or_model}) | Reason: Groq bypassed or exhausted")
                # ROOT-CAUSE FIX (diagram failures): the nemotron reasoner models
                # spend most of max_tokens on a separate `reasoning` field, leaving
                # `content` empty/truncated. `extra_body.reasoning.exclude=True`
                # tells OpenRouter to suppress reasoning so the FULL token budget
                # goes to the actual JSON answer.
                resp = _get_openrouter().chat.completions.create(
                    model=or_model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a precise JSON generator. Return ONLY valid JSON. No markdown. No text outside JSON."
                        },
                        {"role": "user", "content": prompt}
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=45.0,
                    extra_body={"reasoning": {"exclude": True}},
                )
                msg = resp.choices[0].message
                raw = msg.content
                parsed = _repair_json(raw)
                # Fallback: if a reasoner still routed its JSON into the `reasoning`
                # field (content empty), salvage JSON from there too.
                if parsed is None:
                    reasoning_txt = getattr(msg, "reasoning", None) or ""
                    if reasoning_txt:
                        parsed = _repair_json(reasoning_txt)
                token_tracker.record_usage("openrouter", est_prompt_tokens)
                if parsed is not None:
                    log.info(f"[{task_name}] OpenRouter ({or_model}) success")
                    _provider_failures["openrouter_text"] = 0
                    if use_cache:
                        _set_cached_response(task_name, prompt, parsed)
                    return parsed
                log.warning(f"[{task_name}] OpenRouter ({or_model}) returned unparseable JSON — trying next model")
            except Exception as e:
                log.warning(f"[{task_name}] OpenRouter ({or_model}) error: {e} — trying next model")
        _mark_failed("openrouter_text")



    # ── LAST RESORT: Gemini ───────────────────────────────────────────────
    if _is_healthy("gemini"):
        try:
            log.warning(f"[routing] [{task_name}] LAST RESORT: Gemini 2.0 Flash | Reason: Groq and OpenRouter unavailable")
            gemini_text_model, _ = _get_gemini()
            resp = gemini_text_model.generate_content(
                f"{prompt}\n\nReturn ONLY valid JSON. No markdown. No explanation."
            )
            parsed = _repair_json(resp.text)
            if parsed is not None:
                log.info(f"[{task_name}] Gemini fallback success")
                return parsed
        except Exception as e:
            _mark_failed("gemini")
            log.error(f"[{task_name}] Gemini error: {e}")

    log.error(f"[{task_name}] ALL TEXT PROVIDERS FAILED")
    return None


def generate_text_json_premium(
    prompt: str,
    task_name: str = "premium_task",
    max_tokens: int = 3072,
    temperature: float = 0.3,
    use_cache: bool = True
) -> Optional[dict | list]:
    """
    HIGH-REASONING JSON generation for the jobs that set the quality ceiling of
    the entire video: Agent 1 (content analysis) and Agent 2 (pedagogy planning).

    Difference from generate_text_json():
      • Leads with GROQ_PREMIUM_TEXT_MODELS (openai/gpt-oss-120b first — the
        strongest reasoner) instead of the speed-first general chain.
      • On any Groq miss, transparently delegates to generate_text_json() so the
        full free OpenRouter → Gemini fallback chain still applies.
    This means better structural understanding of the document up-front, which
    fixes shallow explanations and mis-planned scene flow downstream.
    """
    from core.token_tracker import token_tracker

    if use_cache:
        cached = _get_cached_response(task_name, prompt)
        if cached is not None and isinstance(cached, (dict, list)):
            return cached

    est_prompt_tokens = (len(prompt) // 3) + max_tokens
    can_use_groq = _is_healthy("groq") and token_tracker.can_use_groq(est_prompt_tokens)

    if can_use_groq:
        for model_name in GROQ_PREMIUM_TEXT_MODELS:
            pm_kwargs = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": "You are a precise JSON generator and expert reasoner. Return ONLY valid JSON. No markdown. No explanation."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
                "timeout": 55.0,
            }
            if model_name in _GROQ_JSON_MODE_SUPPORTED:
                pm_kwargs["response_format"] = {"type": "json_object"}

            # V17: Retry-before-fallback + pacing for premium path
            for attempt in range(len(_RETRY_BACKOFFS) + 1):
                try:
                    _pace_premium_call()
                    log.info(f"[routing] [{task_name}] PREMIUM Tier: Groq ({model_name}) | attempt {attempt + 1}")
                    resp = _get_groq().chat.completions.create(**pm_kwargs)
                    raw = resp.choices[0].message.content
                    parsed = _repair_json(raw)
                    usage_tokens = getattr(resp, "usage", None)
                    total_tok = usage_tokens.total_tokens if usage_tokens else est_prompt_tokens
                    token_tracker.record_usage("groq", total_tok)
                    if parsed is not None:
                        log.info(f"[{task_name}] PREMIUM Groq ({model_name}) success ({total_tok} tokens)")
                        _provider_failures["groq"] = 0
                        if use_cache:
                            _set_cached_response(task_name, prompt, parsed)
                        return parsed
                    log.warning(f"[{task_name}] PREMIUM Groq ({model_name}) unparseable — trying next model")
                    break  # unparseable → next model, not retry
                except Exception as e:
                    err_str = str(e)
                    # Per-DAY exhaustion → rotate key or next model
                    if "tpd" in err_str.lower() or "tokens per day" in err_str.lower() or "per day" in err_str.lower():
                        log.warning(f"[{task_name}] PREMIUM Groq ({model_name}) TPD hit: {err_str[:80]}")
                        if _rotate_groq_key():
                            continue
                        break
                    # Transient 429 → backoff retry SAME model
                    if _is_transient_rate_limit(err_str) and attempt < len(_RETRY_BACKOFFS):
                        wait = _RETRY_BACKOFFS[attempt]
                        log.warning(f"[{task_name}] PREMIUM Groq ({model_name}) transient 429 — backoff {wait}s (attempt {attempt + 1})")
                        time.sleep(wait)
                        continue
                    log.warning(f"[{task_name}] PREMIUM Groq ({model_name}) error: {err_str[:120]} — trying next")
                    break

    # Delegate to the standard router for the full free fallback chain.
    log.info(f"[{task_name}] PREMIUM tier exhausted/unavailable — delegating to standard router")
    return generate_text_json(prompt, task_name=task_name, max_tokens=max_tokens,
                              temperature=temperature, use_cache=use_cache)


def generate_text_raw(
    prompt: str,
    task_name: str = "text_raw",
    max_tokens: int = 2048,
    temperature: float = 0.5
) -> Optional[str]:

    """
    Text-in → raw text-out (not JSON). Groq primary, OpenRouter secondary, Gemini last resort.
    """
    if _is_healthy("groq"):
        for model_name in GROQ_TEXT_MODELS:
            try:
                log.info(f"[{task_name}] Tier 1: Groq ({model_name})")
                resp = _get_groq().chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=30.0
                )
                result = resp.choices[0].message.content
                if result:
                    _provider_failures["groq"] = 0
                    return result.strip()
            except Exception as e:
                log.warning(f"[{task_name}] Groq error with model {model_name}: {e}")
        _mark_failed("groq")

    # Tier 2 OpenRouter
    if _is_healthy("openrouter_text"):
        try:
            log.info(f"[{task_name}] Tier 2: OpenRouter ({OPENROUTER_TEXT_MODEL})")
            resp = _get_openrouter().chat.completions.create(
                model=OPENROUTER_TEXT_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=30.0
            )
            result = resp.choices[0].message.content
            if result:
                _provider_failures["openrouter_text"] = 0
                return result.strip()
        except Exception as e:
            _mark_failed("openrouter_text")

    # Last resort Gemini
    if _is_healthy("gemini"):
        try:
            log.warning(f"[{task_name}] LAST RESORT: Gemini")
            gemini_text_model, _ = _get_gemini()
            resp = gemini_text_model.generate_content(prompt)
            return resp.text.strip() if resp.text else None
        except Exception as e:
            _mark_failed("gemini")
            log.error(f"[{task_name}] Gemini error: {e}")

    return None


# ══════════════════════════════════════════════════════════════════════════
# PUBLIC API — VISION TASKS
# ══════════════════════════════════════════════════════════════════════════

def analyze_image_json(
    image_path: str,
    prompt: str,
    task_name: str = "vision_task",
    max_tokens: int = 2000
) -> Optional[dict | list]:
    """
    Image + text → JSON-out.
    
    Tier 1: OpenRouter Qwen2.5-VL-32B  ← best diagram understanding
    Tier 2: OpenRouter Qwen2.5-VL-7B   ← faster fallback
    Tier 3: Groq LLaMA 4 Scout Vision  ← already in stack
    Last:   Gemini Vision               ← absolute last resort
    
    Returns parsed dict/list or None.
    """
    if not image_path or not Path(image_path).exists():
        log.error(f"[{task_name}] Image not found: {image_path}")
        return None

    img_b64 = _encode_image(image_path)
    img_url = f"data:image/png;base64,{img_b64}"

    full_prompt = (
        f"{prompt}\n\n"
        "CRITICAL: Return ONLY valid JSON. "
        "No markdown fences. No explanation text. No preamble. "
        "Start your response with {{ or [ immediately."
    )

    # ── TIER 1: Qwen2.5-VL-32B via OpenRouter ────────────────────────────
    if _is_healthy("openrouter_32b"):
        try:
            log.info(f"[{task_name}] Tier 1: Qwen2.5-VL-32B")
            from openai import RateLimitError as ORRateLimit
            resp = _get_openrouter().chat.completions.create(
                model=QWEN_VL_32B,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": full_prompt},
                        {"type": "image_url", "image_url": {"url": img_url}}
                    ]
                }],
                max_tokens=max_tokens,
                temperature=0.1,
                timeout=30.0
            )
            raw = resp.choices[0].message.content
            parsed = _repair_json(raw)
            if parsed is not None:
                log.info(f"[{task_name}] Qwen2.5-VL-32B success")
                _provider_failures["openrouter_32b"] = 0
                return parsed
            log.warning(f"[{task_name}] Qwen-32B returned unparseable response")
        except Exception as e:
            _mark_failed("openrouter_32b")
            log.warning(f"[{task_name}] Qwen-32B error: {e}")

    # ── TIER 2: Qwen2.5-VL-7B via OpenRouter ─────────────────────────────
    if _is_healthy("openrouter_7b"):
        try:
            log.info(f"[{task_name}] Tier 2: Qwen2.5-VL-7B")
            resp = _get_openrouter().chat.completions.create(
                model=QWEN_VL_7B,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": full_prompt},
                        {"type": "image_url", "image_url": {"url": img_url}}
                    ]
                }],
                max_tokens=max_tokens,
                temperature=0.1,
                timeout=30.0
            )
            raw = resp.choices[0].message.content
            parsed = _repair_json(raw)
            if parsed is not None:
                log.info(f"[{task_name}] Qwen2.5-VL-7B success")
                _provider_failures["openrouter_7b"] = 0
                return parsed
        except Exception as e:
            _mark_failed("openrouter_7b")
            log.warning(f"[{task_name}] Qwen-7B error: {e}")

    # ── TIER 2b/2c: Free vision fallbacks via OpenRouter ─────────────────
    # gemini-2.5-flash:free (1M ctx), llama-4-maverick:free, gemini-2.0-flash-exp:free
    if _is_healthy("openrouter_text"):
        for free_vis_model in OPENROUTER_VISION_FREE_MODELS:
            try:
                log.info(f"[{task_name}] Tier 2b/2c: OpenRouter free vision ({free_vis_model})")
                resp = _get_openrouter().chat.completions.create(
                    model=free_vis_model,
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": full_prompt},
                            {"type": "image_url", "image_url": {"url": img_url}}
                        ]
                    }],
                    max_tokens=max_tokens,
                    temperature=0.1,
                    timeout=45.0
                )
                raw = resp.choices[0].message.content
                parsed = _repair_json(raw)
                if parsed is not None:
                    log.info(f"[{task_name}] OpenRouter free vision ({free_vis_model}) success")
                    return parsed
                log.warning(f"[{task_name}] OpenRouter free vision ({free_vis_model}) unparseable — trying next")
            except Exception as e:
                log.warning(f"[{task_name}] OpenRouter free vision ({free_vis_model}) error: {e} — trying next")

    # ── TIER 3: Groq Vision (DISABLED — preview models removed by Groq) ──
    # GROQ_VISION_MODELS is intentionally empty; this loop is a no-op kept so
    # vision can be re-enabled instantly if Groq ships a new vision model.

    if GROQ_VISION_MODELS and _is_healthy("groq"):
        for model_name in GROQ_VISION_MODELS:

            try:
                log.info(f"[{task_name}] Tier 3: Groq Vision (model={model_name})")
                resp = _get_groq().chat.completions.create(
                    model=model_name,
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": full_prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": img_url}
                            }
                        ]
                    }],
                    response_format={"type": "json_object"},
                    temperature=0.1,
                    max_tokens=max_tokens,
                    timeout=30.0
                )
                raw = resp.choices[0].message.content
                parsed = _repair_json(raw)
                if parsed is not None:
                    log.info(f"[{task_name}] Groq Vision ({model_name}) success")
                    return parsed
            except Exception as e:
                log.warning(f"[{task_name}] Groq Vision error with model {model_name}: {e}")
        # If all Groq models fail, then mark provider as failed
        _mark_failed("groq")

    # ── LAST RESORT: Gemini Vision ────────────────────────────────────────
    if _is_healthy("gemini"):
        try:
            log.warning(f"[{task_name}] LAST RESORT: Gemini Vision")
            import PIL.Image
            pil_img = PIL.Image.open(image_path)
            _, gemini_vision_model = _get_gemini()
            resp = gemini_vision_model.generate_content([
                full_prompt, pil_img
            ])
            parsed = _repair_json(resp.text)
            if parsed is not None:
                log.info(f"[{task_name}] Gemini Vision fallback success")
                return parsed
        except Exception as e:
            _mark_failed("gemini")
            log.error(f"[{task_name}] Gemini Vision error: {e}")

    log.error(f"[{task_name}] ALL VISION PROVIDERS FAILED")
    return None


def get_provider_health() -> dict:
    """Returns current health status of all providers."""
    return {
        provider: {
            "healthy": _is_healthy(provider),
            "failures": count
        }
        for provider, count in _provider_failures.items()
    }
