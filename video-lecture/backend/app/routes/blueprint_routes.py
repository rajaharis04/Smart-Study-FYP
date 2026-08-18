from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse
from app.database.models import User
from app.auth.dependencies import get_current_teacher
from app.rag.llm_client import get_llm_client
from app.rag.rag_service import get_rag_service
from app.services.blueprint_pipeline import BlueprintPipeline
from app.config import settings
from app.utils.logger import log_info, log_error
import os
import json
import uuid

router = APIRouter(prefix="/api/blueprint", tags=["video-blueprint"])

# Job store for tracking blueprint renders
blueprint_jobs = {}
CACHED_DRAFT_PATH = "static/uploads/cached_blueprint.json"

def save_cached_draft(blueprint: dict, extra_info: dict = None):
    try:
        os.makedirs(os.path.dirname(CACHED_DRAFT_PATH), exist_ok=True)
        # Load existing extra info if not provided
        vlm_pages_analyzed = 0
        extracted_images = []
        extracted_images_count = 0
        last_video_url = None
        if os.path.exists(CACHED_DRAFT_PATH):
            try:
                with open(CACHED_DRAFT_PATH, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                    vlm_pages_analyzed = existing.get("vlm_pages_analyzed", 0)
                    extracted_images = existing.get("extracted_images", [])
                    extracted_images_count = existing.get("extracted_images_count", 0)
                    last_video_url = existing.get("last_video_url")
            except Exception:
                pass

        if extra_info:
            vlm_pages_analyzed = extra_info.get("vlm_pages_analyzed", vlm_pages_analyzed)
            extracted_images = extra_info.get("extracted_images", extracted_images)
            extracted_images_count = extra_info.get("extracted_images_count", extracted_images_count)
            if "last_video_url" in extra_info:
                last_video_url = extra_info["last_video_url"]

        data = {
            "blueprint": blueprint,
            "vlm_pages_analyzed": vlm_pages_analyzed,
            "extracted_images": extracted_images,
            "extracted_images_count": extracted_images_count,
            "last_video_url": last_video_url,
            "timestamp": time.time() if 'time' in globals() else 0.0
        }
        # In case time is not imported in global scope yet
        import time as _time
        data["timestamp"] = _time.time()

        with open(CACHED_DRAFT_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        log_info(f"[Blueprint Cache] Saved last draft to {CACHED_DRAFT_PATH}")
    except Exception as e:
        log_error(f"[Blueprint Cache] Failed to save last draft: {e}")

@router.get("/last-draft")
async def get_last_draft():
    if not os.path.exists(CACHED_DRAFT_PATH):
        return JSONResponse(content={"status": "empty"})
    try:
        with open(CACHED_DRAFT_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return JSONResponse(content={"status": "success", **data})
    except Exception as e:
        log_error(f"[Blueprint Cache] Failed to load last draft: {e}")
        return JSONResponse(content={"status": "empty", "error": str(e)})

@router.post("/clear-draft")
async def clear_last_draft():
    if os.path.exists(CACHED_DRAFT_PATH):
        try:
            os.remove(CACHED_DRAFT_PATH)
            log_info("[Blueprint Cache] Cleared last draft cache file.")
            return JSONResponse(content={"status": "success"})
        except Exception as e:
            log_error(f"[Blueprint Cache] Failed to delete last draft cache file: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    return JSONResponse(content={"status": "success"})

@router.post("/generate-draft")
async def generate_draft_blueprint(
    file: UploadFile = File(None),
    text_input: str = Form(None)
):
    """
    Phase 1: Extracts text + images from PDF, runs VLM vision analysis on each page,
    then asks LLM to generate a 5-scene JSON blueprint enriched with visual understanding.
    Alternatively, accepts raw text for quick testing.
    """
    if not file and not text_input:
        raise HTTPException(status_code=400, detail="Must provide either a PDF file or raw text.")

    text = ""
    extracted_images = []
    vlm_pages = []

    try:
        if file:
            if not file.filename.lower().endswith('.pdf'):
                raise HTTPException(status_code=400, detail="Only PDF files are supported.")
                
            # Save temp PDF
            temp_pdf = f"static/uploads/pdfs/temp_{uuid.uuid4().hex}.pdf"
            os.makedirs(os.path.dirname(temp_pdf), exist_ok=True)
            with open(temp_pdf, "wb") as f:
                content = await file.read()
                f.write(content)

            # Extract text
            rag = get_rag_service()
            text = rag.extract_text_from_pdf(temp_pdf)

            # Extract embedded images from PDF
            extracted_images = rag.extract_images_from_pdf(temp_pdf)

            if not text or len(text) < 50:
                os.remove(temp_pdf)
                raise HTTPException(status_code=400, detail="Could not extract enough text from PDF.")

            # ── VLM Vision Analysis (Groq LLaMA 4 Scout) ────────────────────────
            try:
                from app.services.vlm_service import process_pdf_with_vlm, analyze_diagram_with_vlm
                import tempfile
                vlm_temp_dir = tempfile.mkdtemp(prefix="vlm_pages_")
                llm = get_llm_client()
                
                # Analyze full pages
                vlm_pages = process_pdf_with_vlm(temp_pdf, llm, vlm_temp_dir, max_pages=8)
                log_info(f"VLM analysis complete: {len(vlm_pages)} pages analyzed")

                # ── VECTOR DIAGRAM FIX ────────────────────────────────────
                # extract_images_from_pdf only finds embedded raster images.
                # Vector-drawn diagrams (Dijkstra graphs, flowcharts, etc.) are
                # invisible to it. VLM already rendered every page as a PNG and
                # set has_diagram=True when it saw a diagram. Inject those page
                # renders into extracted_images so FIX4 doesn't downgrade them
                # to bullets_only.
                for _pg in vlm_pages:
                    if _pg.get("has_diagram") and _pg.get("image_path"):
                        _img = _pg["image_path"]
                        if _img not in extracted_images:
                            extracted_images.append(_img)
                            log_info(f"[VectorDiagramFix] Injected VLM page render: {_img}")

                # Analyze extracted diagrams for spatial awareness (Limit to 3 to save API time)
                diagram_spatial_data = {}
                if extracted_images:
                    for i, img_path in enumerate(extracted_images[:3]):
                        coords = analyze_diagram_with_vlm(img_path, llm)
                        if coords:
                            diagram_spatial_data[img_path] = coords
                
            except Exception as vlm_err:
                log_error(f"VLM analysis skipped (non-fatal): {vlm_err}")
                diagram_spatial_data = {}
                
        elif text_input:
            text = text_input
            diagram_spatial_data = {}
            log_info("Using provided raw text for blueprint generation.")

        if file:
            os.remove(temp_pdf)

        # Force-reset LLM singleton so a stale MockLLMClient can't persist
        import app.rag.llm_client as _llm_mod
        _llm_mod._llm_client = None

        # ── Blueprint Generation (text + VLM + images) ───────────────────────
        llm = get_llm_client()
        log_info(f"[Blueprint] LLM client type: {type(llm).__name__}")
        
        try:
            from core.pedagogical_engine import PedagogicalEngine
            engine = PedagogicalEngine(llm_client=llm)
            blueprint = engine.generate_blueprint_v5(
                document_text=text,
                extracted_images=extracted_images,
                vlm_pages=vlm_pages,
                diagram_spatial_data=diagram_spatial_data
            )
        except Exception as e:
            log_error(f"PedagogicalEngine failed: {e}")
            blueprint = None

        if not blueprint or not isinstance(blueprint, dict) or not blueprint.get("scenes"):
            log_info("[Blueprint] Falling back to monolithic LLM prompt...")
            blueprint = await llm.generate_video_blueprint(
                document_text=text,
                extracted_images=extracted_images,
                vlm_pages=vlm_pages,
                diagram_spatial_data=diagram_spatial_data
            )

        if not blueprint or not isinstance(blueprint, dict) or not blueprint.get("scenes"):
            raise HTTPException(status_code=500, detail="LLM failed to return a valid blueprint.")

        # Save to cache
        save_cached_draft(blueprint, {
            "vlm_pages_analyzed": len(vlm_pages),
            "extracted_images": extracted_images,
            "extracted_images_count": len(extracted_images)
        })

        return JSONResponse(content={
            "status": "success",
            "blueprint": blueprint,
            "vlm_pages_analyzed": len(vlm_pages),
            "extracted_images": extracted_images,  # actual paths, not just count
            "extracted_images_count": len(extracted_images)
        })

    except Exception as e:
        log_error(f"Generate draft failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

import requests
import time

async def _render_task(job_id: str, blueprint_json: dict, user_id: int, avatar_path: str = None):
    # Note: asyncio.WindowsProactorEventLoopPolicy is already set globally in main.py
    import asyncio
            
    try:
        blueprint_jobs[job_id]["status"] = "processing"
        
        # Define progress callback
        def update_progress(progress_pct: int, step_desc: str):
            blueprint_jobs[job_id]["progress"] = progress_pct
            blueprint_jobs[job_id]["current_step"] = step_desc
            
        # V13 Update: We now ALWAYS run the local pipeline.
        # The pipeline itself is now smart enough to delegate the 
        # heavy LIPSINC work to the Kaggle Cloud URL automatically.
        log_info(f"[{job_id}] Running V14 local-cloud hybrid pipeline...")
        
        # Instantiate pipeline locally
        pipeline = BlueprintPipeline()
        if avatar_path:
            video_path = await pipeline.render_blueprint(blueprint_json, avatar_path=avatar_path, progress_callback=update_progress)
        else:
            video_path = await pipeline.render_blueprint(blueprint_json, progress_callback=update_progress)
        
        if video_path:
            filename = os.path.basename(video_path)
            video_url = f"/{settings.VIDEO_FOLDER}/{filename}"
            blueprint_jobs[job_id]["status"] = "completed"
            blueprint_jobs[job_id]["video_url"] = video_url
            blueprint_jobs[job_id]["progress"] = 100
            blueprint_jobs[job_id]["current_step"] = "Done!"
            save_cached_draft(blueprint_json, {"last_video_url": video_url})
        else:
            blueprint_jobs[job_id]["status"] = "failed"
            blueprint_jobs[job_id]["error"] = "Pipeline rendering returned None."
            
        pipeline.cleanup()
            
    except Exception as e:
        log_error(f"Render task {job_id} failed: {e}")
        blueprint_jobs[job_id]["status"] = "failed"
        blueprint_jobs[job_id]["error"] = str(e)

@router.post("/assemble")
async def assemble_video_blueprint(
    background_tasks: BackgroundTasks,
    blueprint_data: str = Form(...),
    avatar_file: UploadFile = File(None)
):
    """
    Phase 2 & 3: Accepts the updated JSON draft and pushes it to background rendering.
    """
    try:
        blueprint_json = json.loads(blueprint_data)
        
        # Save to cache
        save_cached_draft(blueprint_json)
        
        job_id = f"job_{uuid.uuid4().hex[:8]}"
        
        saved_avatar_path = None
        if avatar_file and avatar_file.filename:
            # Use absolute path to ensure FFmpeg can always find it
            avatar_dir = os.path.abspath("static/uploads/avatars")
            os.makedirs(avatar_dir, exist_ok=True)
            saved_avatar_path = os.path.join(avatar_dir, f"{job_id}_{avatar_file.filename}")
            with open(saved_avatar_path, "wb") as f:
                f.write(await avatar_file.read())
        
        blueprint_jobs[job_id] = {
            "status": "queued",
            "video_url": None,
            "error": None
        }
        
        background_tasks.add_task(_render_task, job_id, blueprint_json, 1, saved_avatar_path)
        
        return JSONResponse(content={"status": "success", "job_id": job_id})
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON blueprint.")
    except Exception as e:
        log_error(f"Assemble fail: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{job_id}")
async def get_blueprint_status(job_id: str):
    if job_id not in blueprint_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return JSONResponse(content=blueprint_jobs[job_id])

from pydantic import BaseModel
from typing import Optional

class PublishToSectionReq(BaseModel):
    section_id: int
    title: str
    description: Optional[str] = "AI Generated Video Lecture"
    video_url: str
    duration: Optional[int] = 180

@router.get("/sections")
async def get_teacher_sections():
    """
    Fetch list of available sections from admin_web DB so frontend can populate section selector
    """
    try:
        admin_backend_path = os.path.abspath(
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "admin_web", "backend")
        )
        if admin_backend_path not in sys.path:
            sys.path.insert(0, admin_backend_path)
            
        from app.db.database import SessionLocal
        from app.models.models import Section, Course
        
        db = SessionLocal()
        try:
            sections = db.query(Section).all()
            results = []
            for s in sections:
                course = db.query(Course).filter(Course.id == s.course_id).first()
                c_name = course.name if course else f"Course {s.course_id}"
                label = getattr(s, "section_label", f"Section {s.id}")
                results.append({
                    "id": s.id,
                    "label": f"{c_name} - {label} (ID: {s.id})",
                    "course_name": c_name
                })
            return JSONResponse(content={"status": "success", "sections": results})
        finally:
            db.close()
    except Exception as e:
        log_error(f"[PublishToSection] Failed to fetch sections: {e}")
        return JSONResponse(content={"status": "error", "sections": []})


@router.post("/publish-to-section")
async def publish_video_to_teacher_section(req: PublishToSectionReq):
    """
    Publish a generated video lecture directly into a Teacher Panel section DB
    """
    import shutil
    try:
        video_filename = os.path.basename(req.video_url)
        src_path = os.path.join("static", "videos", video_filename)
        if not os.path.exists(src_path):
            # Try absolute path from video_url
            clean_rel = req.video_url.lstrip("/")
            if os.path.exists(clean_rel):
                src_path = clean_rel
            else:
                raise HTTPException(status_code=404, detail=f"Source video file {video_filename} not found.")

        admin_backend_path = os.path.abspath(
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "admin_web", "backend")
        )
        if admin_backend_path not in sys.path:
            sys.path.insert(0, admin_backend_path)

        from app.db.database import SessionLocal
        from app.models.models import Section, Lecture
        
        dest_dir = os.path.join(admin_backend_path, "uploads", "videos")
        os.makedirs(dest_dir, exist_ok=True)

        dest_filename = f"section_{req.section_id}_{int(time.time())}_{video_filename}"
        dest_path = os.path.join(dest_dir, dest_filename)

        shutil.copy2(src_path, dest_path)

        db = SessionLocal()
        try:
            sec = db.query(Section).filter(Section.id == req.section_id).first()
            if not sec:
                raise HTTPException(status_code=404, detail=f"Section {req.section_id} not found.")

            from datetime import datetime as _dt
            lecture = Lecture(
                section_id=sec.id,
                title=req.title or "AI Generated Video Lecture",
                video_url=f"/uploads/videos/{dest_filename}",
                duration=req.duration or 180,
                description=req.description or "AI Generated Video Lecture",
                is_published=True,
                publish_date=_dt.utcnow()
            )
            
            db.add(lecture)
            db.commit()
            db.refresh(lecture)
            log_info(f"[PublishToSection] Successfully published lecture {lecture.id} to Section {sec.id}")
            return JSONResponse(content={
                "status": "success", 
                "message": f"Successfully published to Teacher Panel Section {sec.id}!",
                "lecture_id": lecture.id
            })
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        log_error(f"[PublishToSection] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

