# Attention & Presence Monitor

A self-contained module that runs **while a student watches a generated video**
and, by the end of the session, answers two questions:

1. **Who is watching?** — face recognition against enrolled students (DeepFace / ArcFace).
2. **Were they paying attention?** — a per-frame attentiveness score aggregated
   into a session ratio; if `ratio ≥ ATTENDANCE_THRESHOLD` (default **0.80**) the
   session is marked **Present**, otherwise **Absent**.

It is an attendance/engagement-verification layer bolted onto the existing
video-delivery flow. **It does not touch video generation.**

---

## Architecture at a glance

```
                    ┌───────────────────────────────────────────────┐
   Student webcam   │  CLIENT (captures a frame ~1 fps, base64)      │
        frame  ───► │  → POST /api/attention/frame                  │
                    └───────────────────────┬───────────────────────┘
                                            │
      admin_web/backend/app/api/attention.py│  (routes + Postgres persistence)
      • lazy-imports CV  • never stores images
                                            ▼
   video-lecture/modules/attention_monitor/ │  (PURE, DB-independent CV)
   ┌──────────────┬───────────────┬─────────┴───────┬───────────────┐
   │ landmarks.py │  formulas.py  │    gaze.py       │ recognition.py │
   │ MediaPipe    │  EAR +        │  L2CS-Net        │ DeepFace       │
   │ Face Mesh    │  head-pose    │  (optional)      │ ArcFace        │
   └──────┬───────┴──────┬────────┴────────┬─────────┴───────┬───────┘
          └──────────────┴───── scorer.py ─┴─────────────────┘
                         per-frame is_attentive() + SessionAggregator
```

### Two-layer split (by design)

| Layer | Location | Depends on DB? | Heavy CV deps? |
|-------|----------|:--------------:|:--------------:|
| **Pure CV logic** | `video-lecture/modules/attention_monitor/` | ❌ No | yes (imported lazily) |
| **Routes + persistence** | `admin_web/backend/app/api/attention.py` | ✅ Postgres | no top-level import |

The API layer **lazy-imports** the CV stack inside request handlers. The lean
production backend therefore keeps booting normally even without the CV
libraries installed; CV endpoints just return **HTTP 503** until you run the
backend from the dedicated CV virtualenv.

---

## Files

| File | Responsibility |
|------|----------------|
| `config.py` | Every tunable constant (thresholds, EAR, angles, fps, cosine, flags). |
| `landmarks.py` | MediaPipe Face Mesh wrapper → 468 landmarks per face. |
| `formulas.py` | EAR (eye open/closed) + head-pose via `cv2.solvePnP` → yaw/pitch/roll. |
| `gaze.py` | L2CS-Net gaze estimator (feature-flagged, lazy, non-blocking). |
| `recognition.py` | DeepFace ArcFace embeddings + cosine matching. |
| `scorer.py` | `analyze_frame()` + `SessionAggregator` (ratio, status, edge flags). |
| `../scripts/verify_webcam_loop.py` | Local webcam end-to-end test harness. |

Persistence + API (in `admin_web/backend`):
| File | Responsibility |
|------|----------------|
| `app/api/attention.py` | FastAPI routes; writes Postgres; lazy CV import. |
| `app/models/models.py` | `EnrolledFace`, `AttentionSession`, + `Attendance` columns. |
| `main.py` | Registers the router + auto-migrates the new `attendance` columns. |
| `requirements-attention.txt` | The heavy CV deps (separate venv). |

---

## The maths (spec §4)

**Eye Aspect Ratio (per eye, 6 points):**
```
EAR = (‖p2−p6‖ + ‖p3−p5‖) / (2 · ‖p1−p4‖)
```
Eyes "closed/half-closed" when `EAR < EAR_THRESHOLD` (0.20).

**Head pose:** `cv2.solvePnP` on 6 MediaPipe landmarks (nose, chin, eye corners,
mouth corners) against a generic 3D face model → `cv2.Rodrigues` →
`cv2.RQDecomp3x3` → yaw/pitch/roll. "Frontal" when `|yaw| < 25°` and `|pitch| < 20°`.

**Per-frame STATE (v2):** each frame resolves to exactly ONE state, most-severe
first, so the student sees *why* they are (in)attentive:
```
no_face > multiple_faces > spoof > not_you > drowsy > eyes_closed
        > looking_away > attentive
```
Only `attentive` counts toward the ratio. `attentive` requires: one face, the
enrolled identity (locked), head frontal, eyes open (a short blink is fine),
and gaze on-screen (iris gaze always; L2CS-Net when available).

**Blink vs drowsy (temporal, `temporal.py`):** a brief eye-closure
(≤ `BLINK_MAX_SECONDS`, 0.5s) is a normal **blink** and does NOT break
attention; a continuous closure ≥ `DROWSY_MIN_SECONDS` (1.5s) OR a high
**PERCLOS** (closed-time fraction ≥ 0.45 over a 20s window) is **drowsy**.

**Iris gaze (cheap, per-frame, `formulas.py`):** MediaPipe iris points (468–477)
give a normalized horizontal/vertical offset — "looking away" when it exceeds
`IRIS_H_RATIO_MAX` / `IRIS_V_RATIO_MAX`. The heavy L2CS-Net gaze only confirms.

**Anti-spoof (`liveness.py`):** DeepFace MiniFASNet passive texture check +
behavioural blink check (a real viewer blinks; a static photo has ~0 EAR
variance and never blinks) → `spoof` state / `spoof_suspected` flag.

**Session decision:**
```
attention_ratio = attentive_frames / total_sampled_frames
status = "Present" if attention_ratio ≥ ATTENDANCE_THRESHOLD else "Absent"
```

**Two-tier sampling (CPU):** the client streams ~**3 fps**. Every frame runs the
LIGHT tier (landmarks + EAR + head-pose + iris gaze). The HEAVY models are
THROTTLED per session on the backend:
`recognition` every `RECOGNITION_REFRESH_SECONDS` (4s, identity-locked),
`L2CS-Net gaze` every `GAZE_REFRESH_SECONDS` (2s, face-crop),
`anti-spoof` every `LIVENESS_REFRESH_SECONDS` (5s). A short N-frame majority
vote (`SMOOTHING_WINDOW_FRAMES`) stabilises the DISPLAY state (anti-flicker).

**Edge-case flags (spec §5 + v2):** `left_seat` (no face >30s continuous),
`multiple_faces_detected`, `viewer_changed`, `unrecognized_viewer`,
`drowsy_detected`, `spoof_suspected`.


---

## API (all under `/api`, JWT-protected like the rest of the backend)

| Method & Path | Purpose |
|---------------|---------|
| `GET  /attention/status` | Diagnostics: is CV available? gaze on? config dump. |
| `POST /attention/enroll` | `{images_base64:[...]}` → build + store ArcFace embedding. |
| `POST /attention/session/start` | `{lecture_id?, image_base64?}` → create session; start recognition. |
| `POST /attention/frame` | `{session_id, image_base64}` → per-frame metrics (image discarded). |
| `POST /attention/session/end` | `{session_id}` → finalize ratio/status; write `AttentionSession` + `Attendance`. |
| `GET  /attention/report/{student_id}` | Session history (self only). |

`student_id` maps to the **real** `students` table (decision #2). The final
verdict updates the existing `attendance` row's `is_present` plus the new
`attention_ratio / attention_status / attention_flags / attention_marked_at`
columns.

---

## Privacy (spec §6 — enforced in code)

- Frames arrive base64, are decoded to an in-memory `np.ndarray`, processed,
  then explicitly `del`-eted in a `finally` block.
- **No `cv2.imwrite`, no image bytes in the DB** — only derived numbers,
  booleans, angles, ratios, and flags are stored.
- Enrollment stores only the **512-d embedding vector**, never the photos.

---

## Setup

Use **Python 3.10–3.12** in a dedicated virtualenv (**not 3.13** — MediaPipe/
TensorFlow have no 3.13 wheels yet). On this machine use **Python 3.12**:

```bash
cd admin_web/backend
py -3.12 -m venv .venv-attention
.venv-attention\Scripts\activate            # Windows
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-attention.txt
python run.py                                # or: uvicorn main:app --port 8001
```

Confirm: open `http://localhost:8001/api/attention/status` → `cv_available: true`.

**Local pipeline test (no server/DB needed) — keep the same venv active:**
```bash
.venv-attention\Scripts\activate
python video-lecture/scripts/verify_webcam_loop.py --enroll --seconds 60
```

Gaze (optional): see `video-lecture/external/L2CS-Net/SETUP.md`.


---

## Configuration (env overrides)

All constants live in `config.py` and can be overridden by env vars, e.g.:

| Env var | Default | Meaning |
|---------|:-------:|---------|
| `ATTN_ATTENDANCE_THRESHOLD` | `0.80` | Present/Absent cut-off. |
| `ATTN_EAR_THRESHOLD` | `0.20` | Eye open/closed cut-off. |
| `ATTN_HEAD_YAW_MAX_DEG` | `25` | Frontal yaw bound. |
| `ATTN_HEAD_PITCH_MAX_DEG` | `20` | Frontal pitch bound. |
| `ATTN_SAMPLE_FPS` | `1.0` | Sampling rate. |
| `ATTN_RECOGNITION_COSINE_THRESHOLD` | `0.55` | Identity match cut-off. |
| `ATTN_LEFT_SEAT_SECONDS` | `30` | No-face duration → `left_seat`. |
| `ATTN_ENABLE_GAZE` | `false` | Turn on L2CS-Net gaze gate. |

---

## Out of scope (spec §9)

- Teacher-facing dashboard/UI (backend + storage only).
- YOLO classroom multi-student detection (this is single-student, own-webcam).
- A trained engagement classifier (we use transparent, rule-based scoring).
