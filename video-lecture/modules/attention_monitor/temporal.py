"""
temporal.py — Time-aware signals: blink-vs-drowsy, PERCLOS, smoothing, liveness.

The per-frame maths in `formulas.py` is stateless — it can't tell a normal
BLINK from someone SLEEPING, because both look like "eyes closed" in a single
frame. That distinction is inherently *temporal*: it depends on how LONG the
eyes stay closed and how OFTEN. This module owns that short-term memory.

It is pure Python + numpy (no CV/DB deps) so it stays cheap and unit-testable.
The scorer feeds it one `(timestamp, ear, eyes_open, face_detected)` tuple per
sampled frame and reads back derived temporal signals:

  • blink vs drowsy          — from continuous eye-closure duration
  • PERCLOS                  — fraction of window time with eyes closed (fatigue)
  • no-blink duration        — behavioural liveness (a photo never blinks)
  • EAR variance             — near-zero variance ⇒ suspiciously static (photo)
  • majority-vote smoothing  — stabilises the live state label / ratio

Everything is bounded by a rolling time window (config.PERCLOS_WINDOW_SECONDS),
so memory stays O(frames-in-window) regardless of session length.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Deque, Optional, Tuple

from . import config


# ══════════════════════════════════════════════════════════════════════════
#  Eye-closure tracker  →  blink vs drowsy + PERCLOS + liveness
# ══════════════════════════════════════════════════════════════════════════

@dataclass
class EyeClosureState:
    """Snapshot of the temporal eye signals after ingesting a frame.

    eyes_closed_now       : whether THIS frame's eyes were closed.
    continuous_closed_sec : how long eyes have been continuously closed (0 if open).
    is_blink              : short closure (0 < duration <= BLINK_MAX_SECONDS).
    is_drowsy             : long closure (>= DROWSY_MIN_SECONDS) OR high PERCLOS.
    perclos               : fraction (0..1) of windowed time with eyes closed.
    seconds_since_blink   : time since the last COMPLETED blink (for liveness).
    ear_variance          : variance of EAR across the window (static ⇒ ~0).
    """

    eyes_closed_now: bool = False
    continuous_closed_sec: float = 0.0
    is_blink: bool = False
    is_drowsy: bool = False
    perclos: float = 0.0
    seconds_since_blink: float = 0.0
    ear_variance: float = 1.0


class EyeClosureTracker:
    """Rolling-window tracker that separates blinks from drowsiness.

    Fed one sample per analysed frame via `update()`. Uses wall-clock-ish
    timestamps supplied by the caller (seconds, monotonic) so it is robust to
    variable frame intervals (the sampler may not hit exactly SAMPLE_FPS).
    """

    def __init__(
        self,
        *,
        window_seconds: Optional[float] = None,
        blink_max_seconds: Optional[float] = None,
        drowsy_min_seconds: Optional[float] = None,
        perclos_threshold: Optional[float] = None,
        ear_threshold: Optional[float] = None,
    ) -> None:
        self.window_seconds = (
            window_seconds if window_seconds is not None else config.PERCLOS_WINDOW_SECONDS
        )
        self.blink_max_seconds = (
            blink_max_seconds if blink_max_seconds is not None else config.BLINK_MAX_SECONDS
        )
        self.drowsy_min_seconds = (
            drowsy_min_seconds if drowsy_min_seconds is not None else config.DROWSY_MIN_SECONDS
        )
        self.perclos_threshold = (
            perclos_threshold if perclos_threshold is not None else config.PERCLOS_THRESHOLD
        )
        self.ear_threshold = (
            ear_threshold if ear_threshold is not None else config.EAR_THRESHOLD
        )

        # (timestamp, ear, closed) samples within the window.
        self._samples: Deque[Tuple[float, float, bool]] = deque()

        # Continuous-closure tracking.
        self._closed_since: Optional[float] = None   # ts when current closure began
        self._last_ts: Optional[float] = None

        # Blink bookkeeping (a blink COMPLETES on reopen after a short closure).
        self._last_blink_ts: Optional[float] = None
        self._first_ts: Optional[float] = None
        self._blink_count: int = 0

    # ──────────────────────────────────────────────────────────────────
    def update(self, timestamp: float, ear: float, eyes_open: bool) -> EyeClosureState:
        """Ingest one frame's eye reading and return the temporal signals.

        Parameters
        ----------
        timestamp : float
            Monotonic seconds for this frame.
        ear : float
            The averaged eye-aspect-ratio for this frame.
        eyes_open : bool
            Whether EAR >= threshold this frame (open).
        """
        closed = not eyes_open
        if self._first_ts is None:
            self._first_ts = timestamp

        # ── Maintain the continuous-closure timer ──────────────────────
        if closed:
            if self._closed_since is None:
                self._closed_since = timestamp
            continuous = timestamp - self._closed_since
        else:
            # Eyes are open now. If we WERE closed for a short burst, that was
            # a completed blink.
            if self._closed_since is not None:
                closed_duration = (self._last_ts or timestamp) - self._closed_since
                if 0.0 < closed_duration <= self.blink_max_seconds:
                    self._last_blink_ts = timestamp
                    self._blink_count += 1
            self._closed_since = None
            continuous = 0.0

        # ── Push sample + drop anything outside the window ─────────────
        self._samples.append((timestamp, float(ear), closed))
        cutoff = timestamp - self.window_seconds
        while self._samples and self._samples[0][0] < cutoff:
            self._samples.popleft()

        # ── PERCLOS: fraction of windowed samples with eyes closed ─────
        n = len(self._samples)
        closed_count = sum(1 for _, _, c in self._samples if c)
        perclos = (closed_count / n) if n > 0 else 0.0

        # ── EAR variance across the window (static photo ⇒ ~0) ─────────
        ear_variance = _variance([e for _, e, _ in self._samples])

        # ── Blink vs drowsy decision ───────────────────────────────────
        is_drowsy = (
            continuous >= self.drowsy_min_seconds
            or perclos >= self.perclos_threshold
        )
        # A "blink-ish" current closure that hasn't yet crossed into drowsy.
        is_blink = closed and (0.0 < continuous < self.drowsy_min_seconds) and not is_drowsy

        # ── Seconds since last completed blink (for liveness) ──────────
        if self._last_blink_ts is not None:
            seconds_since_blink = timestamp - self._last_blink_ts
        else:
            # No blink observed yet — measure from first sample seen.
            seconds_since_blink = timestamp - (self._first_ts or timestamp)

        self._last_ts = timestamp

        return EyeClosureState(
            eyes_closed_now=closed,
            continuous_closed_sec=continuous,
            is_blink=is_blink,
            is_drowsy=is_drowsy,
            perclos=perclos,
            seconds_since_blink=seconds_since_blink,
            ear_variance=ear_variance,
        )

    # ──────────────────────────────────────────────────────────────────
    @property
    def blink_count(self) -> int:
        """Total completed blinks observed this session."""
        return self._blink_count


# ══════════════════════════════════════════════════════════════════════════
#  State smoother  →  majority vote over the last N frames (anti-flicker)
# ══════════════════════════════════════════════════════════════════════════

class StateSmoother:
    """Stabilises the per-frame state label using a sliding majority vote.

    A single stray frame (one misdetected "looking away") shouldn't flip the
    live badge. We keep the last N raw states and return the most common one as
    the DISPLAY state. The raw per-frame verdict is still used for the session
    ratio; smoothing is about the on-screen experience and robustness.
    """

    def __init__(self, window_frames: Optional[int] = None) -> None:
        self.window_frames = (
            window_frames if window_frames is not None else config.SMOOTHING_WINDOW_FRAMES
        )
        self._window: Deque[str] = deque(maxlen=max(1, self.window_frames))

    def update(self, state: str) -> str:
        """Add a raw state and return the smoothed (majority) state."""
        self._window.append(state)
        return self.smoothed

    @property
    def smoothed(self) -> str:
        """Current majority state (ties resolved toward the most recent)."""
        if not self._window:
            return config.STATE_NO_FACE
        counts: dict[str, int] = {}
        for s in self._window:
            counts[s] = counts.get(s, 0) + 1
        best_state = self._window[-1]
        best_count = -1
        # Iterate newest→oldest so the most recent wins ties.
        for s in reversed(self._window):
            c = counts[s]
            if c > best_count:
                best_count = c
                best_state = s
        return best_state


# ══════════════════════════════════════════════════════════════════════════
#  Internals
# ══════════════════════════════════════════════════════════════════════════

def _variance(values: list[float]) -> float:
    """Population variance of a list (0.0 for <2 samples)."""
    n = len(values)
    if n < 2:
        return 1.0  # not enough data → treat as "varied" (non-suspicious)
    mean = sum(values) / n
    return sum((v - mean) ** 2 for v in values) / n
