# SmartStudyInstructor — Complete Detailed Tech Stack

> Yeh document poore system ka har chhoti se chhoti technical detail cover karta hai:
> exact libraries, versions, kaam, data flow, aur har component ka role.

---

## Table of Contents
1. [System Overview](#1-system-overview)
2. [Complete Dependency List (Exact Versions)](#2-complete-dependency-list-exact-versions)
3. [Layer-by-Layer Tech Stack](#3-layer-by-layer-tech-stack)
4. [Directory Structure](#4-directory-structure)
5. [Video Generation Pipeline (9 Stages)](#5-video-generation-pipeline-9-stages)
6. [AI Provider Routing System](#6-ai-provider-routing-system)
7. [Database Schema](#7-database-schema)
8. [End-to-End Data Flow](#8-end-to-end-data-flow)
9. [Configuration Reference](#9-configuration-reference)

---

## 1. System Overview

SmartStudyInstructor ek **AI-powered educational video generator** hai. Teacher PDF upload karta hai,
system automatically ek **complete narrated lecture video** banata hai jisme:

- Lip-synced teacher avatar
- Word-synced animated diagrams (SVG)
- Slide-in bullet points
- Burned-in subtitles
- Background ambient music

**Core Philosophy:**
- 100% free AI models (Groq + OpenRouter free tier + Gemini fallback)
- Local-first (SQLite, local ChromaDB, local file storage)
- Pure FFmpeg (no MoviePy), Playwright (no Selenium)
- GPU work offloaded to free Kaggle T4

---

## 2. Complete Dependency List (Exact Versions)

Source: `requirements.txt`

| Package | Version | Purpose |
|---------|---------|---------|
| **fastapi** | 0.104.1 | Async web framework — API endpoints |
| **uvicorn[standard]** | 0.24.0 | ASGI server jo FastAPI run karta hai |
| **sqlalchemy** | 2.0.23 | ORM — database models aur queries |
| **pydantic** | 2.5.0 | Request/response validation + schemas |
| **pydantic-settings** | 2.1.0 | `.env` file se config load karna |
| **python-dotenv** | 1.0.0 | Environment variables load karna |
| **python-multipart** | 0.0.6 | File uploads (PDF) handle karna |
| **pyjwt** | 2.8.0 | JWT authentication tokens |
| **passlib[bcrypt]** | 1.7.4 | Password hashing framework |
| **bcrypt** | 4.1.1 | bcrypt hashing algorithm |
| **chromadb** | 0.4.14 | Vector database — RAG embeddings store |
| **sentence-transformers** | 2.2.2 | Text embeddings (all-MiniLM-L6-v2) |
| **pypdf** | 3.17.1 | PDF text extraction (basic) |
| **pdfplumber** | 0.10.3 | PDF text + table extraction (advanced) |
| **pymupdf** | 1.23.8 | PDF → images conversion (fitz) |
| **opencv-python** | 4.8.1.78 | Image processing (YOLO vision) |
| **ultralytics** | 8.0.234 | YOLOv8 — phone detection (proctoring) |
| **pillow** | 10.1.0 | Image manipulation |
| **requests** | 2.31.0 | HTTP client (Kaggle, APIs) |
| **torch** | 2.1.1 | Deep learning backend (YOLO, embeddings) |
| **reportlab** | 4.0.7 | PDF report generation (session reports) |
| **google-generativeai** | 0.3.0 | Gemini API client (LLM fallback) |
| **groq** | >=0.4.0 | Groq LLM client (primary text/vision) |
| **numpy** | 1.26.1 | Numerical operations |

**Runtime dependencies (not in requirements.txt, installed separately):**
- **edge-tts** — Microsoft Edge Text-to-Speech (free voice synthesis)
- **playwright** — headless Chromium for HTML → video recording
- **FFmpeg** — system-level binary for video/audio processing
- **openai** — Python SDK (used for OpenRouter API, OpenAI-compatible)
- **Jinja2** — HTML templating (FastAPI dependency)

---

## 3. Layer-by-Layer Tech Stack

### 3.1 Web / API Layer
- **Framework:** FastAPI 0.104.1 (async)
- **Server:** Uvicorn 0.24.0 (ASGI)
- **Entry:** `backend/run.py` → `backend/app/main.py`
- **Bind:** `0.0.0.0:8000`
- **Middleware:** CORS (allow all origins)
- **Windows fix:** `WindowsProactorEventLoopPolicy` (Playwright subprocess ke liye zaroori)
- **Static mounts:**
  - `/static` → `static/` folder
  - `/assets` → `frontend/` folder
- **Route registration:** Deferred (startup deadlock prevent karne ke liye routes end pe register hote hain)
- **Docs:** Auto-generated Swagger at `/docs`, OpenAPI at `/openapi.json`

### 3.2 Authentication Layer
Files: `app/auth/jwt_handler.py`, `app/auth/password_utils.py`, `app/auth/dependencies.py`

- **Algorithm:** HS256 JWT
- **Token expiry:** 24 hours (`JWT_EXPIRATION_HOURS`)
- **Password:** bcrypt hash (passlib wrapper)
- **Flow:**
  1. Login → username/password verify → JWT token issue
  2. Har protected request → `Authorization: Bearer <token>` header
  3. `get_current_user()` dependency token decode karke `User` object return karta hai
- **Roles:** `admin`, `teacher`, `student` (role-based access control)

### 3.3 Database Layer
Files: `app/database/db.py`, `app/database/models.py`, `app/database/schemas.py`

- **Engine:** SQLite (`smart_study.db` file)
- **ORM:** SQLAlchemy 2.0.23
- **Connection URL:** `sqlite:///./smart_study.db`
- **Base:** Declarative Base pattern
- **Session:** `get_db()` dependency (per-request session)
- **13 tables** (details Section 7 mein)

### 3.4 AI / LLM Layer
File: `core/ai_providers.py`

- **Groq SDK** — primary (llama-3.3-70b, gpt-oss-120b, llama-3.1-8b)
- **OpenRouter** (via openai SDK) — free models fallback
- **google-generativeai** — Gemini last resort
- Full routing detail Section 6 mein

### 3.5 RAG (Retrieval) Layer
Files: `app/rag/rag_service.py`, `app/rag/llm_client.py`

- **Vector DB:** ChromaDB 0.4.14 (local persistent, `chroma_data/`)
- **Embeddings:** sentence-transformers `all-MiniLM-L6-v2` (384-dim)
- **Chunk size:** 512 tokens, 50 token overlap
- **Search:** cosine similarity, top-N results
- **Route:** `POST /api/rag/query`

### 3.6 PDF Processing Layer
Files: `app/utils/pdf_to_images.py`, `app/utils/file_handlers.py`

- **pymupdf (fitz):** pages → PNG images (300 DPI)
- **pdfplumber:** structured text + tables
- **pypdf:** basic text fallback

### 3.7 Vision Layer (VLM)
File: `app/services/vlm_service.py`

- **Primary:** `qwen/qwen3-vl-32b-instruct` (OpenRouter)
- **Fallback:** `qwen/qwen3-vl-8b-instruct` → `gemini-2.0-flash-exp:free` → Gemini API
- Extracts: page type, diagram nodes, edges, weights, computation steps, key concepts

### 3.8 TTS (Voice) Layer
File: `core/tts_engine.py`

- **Engine:** edge-tts (Microsoft, free)
- **Output:** MP3/WAV audio + word-level timestamps (WordBoundary events)
- **Subtitles:** SRT + ASS generation
- **Math preprocessing:** `x²` → "x squared", etc.
- **Async:** sab scenes parallel (`asyncio.gather`)

### 3.9 Animation / Timeline Layer
Files: `core/timeline_builder.py`, `core/animation_brain.py`, `core/camera_utils.py`

- **TimelineBuilder:** word timestamps → animation events JSON
- **AnimationBrain:** 2-stage LLM diagram analysis (comprehend → animate)
- **camera_utils:** Ken Burns / zoom camera math

### 3.10 Diagram Layer
File: `core/diagram_builder.py`

- **Output:** Programmatic SVG (1280×720 canvas)
- **Layouts:** left_to_right, top_to_bottom, radial, grid
- **Collision resolution:** mathematical relaxation (60 iterations)
- **Max nodes:** 24 per diagram

### 3.11 Rendering Layer
Files: `rendering/scene_router.py`, `rendering/playwright_capture.py`, `rendering/ffmpeg_pipeline.py`

- **Templating:** Jinja2 HTML
- **Animation JS:** GSAP (GreenSock)
- **Recording:** Playwright (headless Chromium) → WebM
- **Concurrency:** max 3 parallel browsers
- **Video processing:** FFmpeg (mux, overlay, subtitles, xfade)

### 3.12 Cloud GPU Layer
File: `app/services/kaggle_client.py`

- **Model:** Wav2Lip (lipsync)
- **Host:** Kaggle notebook (free T4 GPU) via ngrok URL
- **Cache:** `static/cache/lipsync/` (audio+avatar hash key)
- **Concurrency:** Semaphore(1) — GPU race prevent

### 3.13 Frontend Layer
Folder: `frontend/`

- Pure HTML + CSS + Vanilla JS (no framework)
- `index.html`, `blueprint_editor.html`
- `js/auth.js` (JWT), `js/api.js` (API calls)
- Server-side Jinja2 templates: `led_player.html`, `student_tuition.html`, `teacher_sessions.html`, `session_report.html`

---

## 4. Directory Structure

```
SmartStudyInstructor/
├── requirements.txt          # Python dependencies
├── Kaggle_Cloud_Engine.ipynb # Wav2Lip GPU notebook
├── README.md
├── backend/
│   ├── run.py                # Server entry point
│   ├── smart_study.db        # SQLite database
│   ├── .env                  # Secrets / config
│   ├── app/
│   │   ├── main.py           # FastAPI app + routes registration
│   │   ├── config.py         # Settings (pydantic-settings)
│   │   ├── auth/             # JWT + bcrypt
│   │   │   ├── jwt_handler.py
│   │   │   ├── password_utils.py
│   │   │   └── dependencies.py
│   │   ├── database/
│   │   │   ├── db.py         # Engine + session
│   │   │   ├── models.py     # 13 SQLAlchemy tables
│   │   │   └── schemas.py    # Pydantic schemas
│   │   ├── rag/
│   │   │   ├── rag_service.py # ChromaDB operations
│   │   │   └── llm_client.py
│   │   ├── routes/
│   │   │   ├── rag.py         # /api/rag/*
│   │   │   └── blueprint_routes.py # video pipeline
│   │   ├── services/
│   │   │   ├── blueprint_pipeline.py # MAIN orchestrator
│   │   │   ├── vlm_service.py         # Qwen-VL analysis
│   │   │   ├── diagram_extractor.py   # PDF diagram crop
│   │   │   ├── scene_router.py
│   │   │   └── kaggle_client.py       # Wav2Lip client
│   │   ├── templates/        # Jinja2 HTML
│   │   └── utils/
│   │       ├── pdf_to_images.py
│   │       ├── file_handlers.py
│   │       ├── tts_processor.py
│   │       └── logger.py
│   ├── core/                 # PIPELINE BRAIN
│   │   ├── ai_providers.py   # LLM router (Groq/OpenRouter/Gemini)
│   │   ├── pedagogical_engine.py # 3.5-agent pipeline
│   │   ├── scene_dna.py      # Scene type classifier
│   │   ├── diagram_builder.py # SVG generator
│   │   ├── tts_engine.py     # edge-tts
│   │   ├── timeline_builder.py # animation events
│   │   ├── animation_brain.py  # diagram animation AI
│   │   ├── camera_utils.py     # Ken Burns math
│   │   └── token_tracker.py    # Groq budget tracker
│   ├── rendering/            # (video output)
│   │   ├── scene_router.py
│   │   ├── playwright_capture.py
│   │   └── ffmpeg_pipeline.py
│   ├── chroma_data/          # ChromaDB persistent store
│   └── static/               # Files (uploads, audio, videos)
├── frontend/                 # HTML/CSS/JS UI
├── docs/
└── static/
```

---

## 5. Video Generation Pipeline (9 Stages)

Main orchestrator: `app/services/blueprint_pipeline.py` → `BlueprintPipeline.render_blueprint()`

### Stage 0: PDF Upload & Extraction
- User PDF upload → `static/uploads/pdfs/`
- `Content` DB record banta hai (with MD5 hash)
- **pymupdf** text extract + **pdfplumber** tables
- **pdf_to_images.py** → har page PNG (300 DPI) → `static/uploads/diagrams/`

### Stage 1: VLM Page Analysis
- File: `vlm_service.py`
- Har page image → Qwen-VL 32B
- Output `vlm_pages`: page_type, diagram_nodes, diagram_edges, weights, computation_steps, key_concepts

### Stage 2: Pedagogical Engine (3.5 Agents)
- File: `core/pedagogical_engine.py` → `generate_blueprint_v5()`

**Agent 1 — Content Analyst** (`analyze_content`)
- LLM: `generate_text_json_premium()` → **gpt-oss-120b** (highest reasoning)
- Input: full text (12000 chars) + VLM context
- Output: course_title, main_topics, teaching_units (scene_mode, diagram metadata, teaching_hook)

**Agent 1.5 — DNA Classifier** (`core/scene_dna.py`)
- Har scene ko DNA type: CONCEPT_DEFINITION, PROCESS_FLOW, CAUSE_EFFECT, COMPARISON, DIAGRAM_SPATIAL, WORKED_EXAMPLE, ANALOGY_BRIDGE, TAKEAWAY_SUMMARY

**Agent 2 — Pedagogical Planner** (`plan_pedagogy`)
- LLM: `generate_text_json()` standard
- Output: teaching_strategies (first_principles/analogy_bridging/socratic_challenge/visual_flowchart), narrative_tone, pacing, aha_moment_trigger

**Agent 3 — Scene Director** (`direct_scenes`)
- LLM: `generate_text_json()` per scene
- DNA-specific prompt + mandatory opening hook rotation (A-G styles)
- Output per scene: heading_left/right, narration (180-260 words), gold_word, left_description, takeaway
- Post: `_derive_bullets_from_narration()` (bullets narration se nikalte hain), `_validate_script_diversity()`

### Stage 3: Diagram Building
- File: `core/diagram_builder.py` → `generate_diagram_svg_and_events()`
- LLM se diagram JSON (nodes, connections, layout) — 8192 max_tokens
- Schema validation + self-correction retry
- Layout algorithm + collision resolution → SVG HTML
- Animation events (node appear, connection draw, weight highlight) word-synced

### Stage 4: TTS Synthesis
- File: `core/tts_engine.py` → `synthesize_all_scenes()`
- edge-tts per scene (parallel async)
- Output: audio_path, words[] (with start_ms/end_ms), srt_path, total_duration_ms

### Stage 5: Timeline Building
- File: `core/timeline_builder.py` → `TimelineBuilder.build()`
- Word timestamps + scene → master timeline JSON
- Events: scene_start, heading_focus, bullet_appear, zoom_word, diagram_appear, diagram_zoom, diagram_flow, component_highlight, subtitle, ken_burns, takeaway, scene_end
- Saved to `static/timelines/{scene_id}.json`

### Stage 6: HTML Rendering
- File: `rendering/scene_router.py` → `render_scene_html()`
- Jinja2 template (DNA-specific) + embedded `window.TIMELINE_DATA`
- GSAP JS animations + SVG diagram + base64 avatar

### Stage 7: Playwright Recording
- File: `rendering/playwright_capture.py` → `record_scene_video()`
- Headless Chromium loads HTML → animations play → screen record → `.webm`
- Semaphore(3): max 3 parallel browsers
- Duration validation vs TTS audio

### Stage 8: Kaggle Lipsync
- File: `app/services/kaggle_client.py` → `generate_lipsync()`
- Audio + avatar image → Wav2Lip on Kaggle T4 → lipsync MP4
- Cache check first (audio+avatar MD5)
- Semaphore(1): GPU serialization
- Fallback: static avatar if no CLOUD_RENDER_URL

### Stage 9: FFmpeg Assembly
- File: `rendering/ffmpeg_pipeline.py`
- Per scene: WebM + audio + lipsync overlay + SRT burn → scene MP4
- All scenes: `concat_with_xfade()` (400ms crossfade)
- Optional: `mix_background_music()` (ambient_music.mp3)
- Output: `static/videos/lecture_XXXXXXXX.mp4`

---

## 6. AI Provider Routing System

File: `core/ai_providers.py`

### Text Tasks — `generate_text_json()`
```
Tier 1 (Groq — fast, free):
  1. llama-3.3-70b-versatile   ← smartest general, clean JSON
  2. openai/gpt-oss-120b       ← highest reasoning backup
  3. llama-3.1-8b-instant      ← small/high-throughput (skip if >4500 tokens)

Tier 2 (OpenRouter — 100% free):
  1. deepseek/deepseek-r1:free       ← strong reasoning
  2. google/gemini-2.0-flash-exp:free ← 1M context
  3. meta-llama/llama-3.3-70b-instruct:free

Tier 3 (last resort):
  Gemini API (gemini-2.0-flash) — own key
```

### Premium Tasks — `generate_text_json_premium()` (Agent 1 + Agent 2)
```
Leads with GROQ_PREMIUM_TEXT_MODELS:
  1. openai/gpt-oss-120b        ← strongest reasoner FIRST
  2. llama-3.3-70b-versatile
Then delegates to standard router (full free fallback chain)
```

### Vision Tasks — `analyze_image_json()`
```
Tier 1:  qwen/qwen3-vl-32b-instruct   ← best diagram spatial
Tier 2:  qwen/qwen3-vl-8b-instruct    ← faster fallback
Tier 2b: google/gemini-2.0-flash-exp:free ← free vision (same OpenRouter key)
Tier 3:  Gemini API vision
```

### Reliability Features
- **Health tracking:** provider 3 failures ke baad bypass (`_MAX_FAILURES = 3`)
- **Token budget:** `token_tracker.py` Groq daily limit track karke preemptive bypass
- **LLM cache:** `static/uploads/llm_cache.json` (MD5 prompt key) — same prompt repeat nahi
- **JSON repair:** `_repair_json()` + `_close_truncated_json()` — markdown fences strip, truncated JSON recover, trailing commas fix
- **Groq key rotation:** `GROQ_API_KEYS` comma-separated pool, rate-limit pe rotate
- **Think stripping:** `<think>...</think>` blocks (Deepseek/Qwen) removed

---

## 7. Database Schema

File: `app/database/models.py` — 13 tables

| Table | Key Columns | Purpose |
|-------|-------------|---------|
| **users** | id, username, email, password_hash, role | Auth + RBAC |
| **contents** | id, user_id, filename, filepath, content_hash | Uploaded PDFs |
| **knowledge_bases** | content_id, collection_name, chroma_collection_id, embedding_model | ChromaDB mapping |
| **sessions** | id, user_id, content_id, session_type, lecture_script | Classroom/tuition |
| **vision_events** | session_id, event_type, confidence, snapshot_path | Phone detection (YOLO) |
| **assessments** | id, content_id, num_questions, passing_score | Quiz config |
| **questions** | assessment_id, question_text, options, correct_answer | Quiz questions |
| **quiz_questions** | document_id, question, options | Legacy quiz |
| **submissions** | student_id, assessment_id, total_score, percentage_score | Quiz attempts |
| **answers** | submission_id, question_id, selected_answer, is_correct | Individual answers |
| **student_responses** | student_id, question_id, selected_answer | Legacy answers |
| **notes** | student_id, content_id, note_content, note_type | Student notes |
| **summaries** | content_id, summary_text, key_points | AI summaries |
| **logs** | user_id, action, resource_type, ip_address | Audit trail |
| **student_notes** | student_id, document_id, content | Legacy notes |

**Relationships:** User 1→N Content, Content 1→1 KnowledgeBase, Content 1→N Session, Session 1→N VisionEvent, Assessment 1→N Question, Submission 1→N Answer

---

## 8. End-to-End Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Teacher uploads PDF (browser → POST)                       │
│    → pymupdf extracts text                                    │
│    → pdf_to_images: pages → PNG (300 DPI)                     │
│    → VLM (Qwen-32B): analyze each page image                  │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. "Generate Video" → PedagogicalEngine.generate_blueprint_v5 │
│    Agent 1 (gpt-oss-120b): content analysis → teaching_units  │
│    Agent 1.5: DNA classification per scene                    │
│    Agent 2: pedagogical strategy per topic                    │
│    Agent 3: narration script per scene (per-scene LLM call)   │
│    → blueprint JSON { scenes: [...] }                         │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. BlueprintPipeline.render_blueprint(blueprint)              │
│    STEP 1: TTS all scenes parallel → audio + word timestamps  │
│    STEP 2: per scene (parallel):                              │
│      - Diagram Builder → SVG (if diagram scene)               │
│      - Timeline Builder → animation events                    │
│      - Scene Router → Jinja2 HTML + GSAP                      │
│      - Playwright → record → WebM                             │
│      - Kaggle → Wav2Lip lipsync MP4                           │
│      - FFmpeg → compose scene MP4 (mux+overlay+subs)          │
│    STEP 3: FFmpeg xfade concat → single lecture               │
│    STEP 4: mix background music                               │
└─────────────────────────────────────────────────────────────┘
                          ↓
        static/videos/lecture_XXXXXXXX.mp4 (FINAL)
```

---

## 9. Configuration Reference

File: `app/config.py` + `.env`

```ini
# ── Authentication ──
JWT_SECRET_KEY=<secret>
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# ── Database ──
DATABASE_URL=sqlite:///./smart_study.db

# ── Server ──
DEBUG=true
HOST=0.0.0.0
PORT=8000

# ── AI API Keys ──
GROQ_API_KEY=<key>
GROQ_API_KEYS=<key1>,<key2>     # rotation pool
OPENROUTER_API_KEY=<key>
GEMINI_API_KEY=<key>

# ── Cloud GPU (Wav2Lip) ──
CLOUD_RENDER_URL=<kaggle-ngrok-url>

# ── Models (defaults) ──
QWEN_VL_32B_MODEL=qwen/qwen2.5-vl-32b-instruct:free
QWEN_VL_7B_MODEL=qwen/qwen-2.5-vl-7b-instruct:free

# ── Asset APIs (optional) ──
PEXELS_API_KEY=<key>            # stock images
GIPHY_API_KEY=<key>             # GIFs

# ── Paths ──
UPLOAD_FOLDER=static/uploads
PDF_UPLOAD_FOLDER=static/uploads/pdfs
AUDIO_FOLDER=static/audio
VIDEO_FOLDER=static/videos
CHROMA_DB_PATH=./chroma_data
YOLO_MODEL_PATH=static/models/yolov8n.pt
```

---

## Key Design Decisions (Kyun Aise Banaya)

| Decision | Reason |
|----------|--------|
| SQLite (not Postgres) | Simple local deployment, FYP scope |
| Free AI models only | Zero operating cost |
| FFmpeg (not MoviePy) | Faster, more reliable, no Python overhead |
| Playwright (not Selenium) | Better async, reliable video recording |
| edge-tts (not ElevenLabs) | Free + word-level timestamps for sync |
| Programmatic SVG (not AI images) | Always crisp, deterministic, editable |
| Kaggle GPU (not local/paid) | Free T4 for Wav2Lip lipsync |
| Word-level TTS timestamps | Exact animation sync, not approximate |
| Multi-tier LLM routing | Reliability — agar ek provider down ho |
| LLM response cache | Same document dobara = no LLM cost |
| Premium routing for Agent 1/2 | Content quality ceiling set karte hain, best model deserve karte hain |

---

*Document generated: covers complete SmartStudyInstructor architecture end-to-end.*
