# -*- coding: utf-8 -*-
"""
SmartStudyInstructor V15 — Playwright Capture (Windows-Safe, Browser-Reusing)

Reuses a single browser and context per render job.
Utilizes Virtual Time Mode by checking window.SCENE_FINISHED flag.
"""
import os
import sys
import time
import json
import uuid
import shutil
import asyncio
import threading
from typing import Dict, Optional
from app.utils.logger import log_info, log_error, log_warning


class PlaywrightRenderer:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self.temp_video_dir = os.path.join(output_dir, f"pw_job_{uuid.uuid4().hex[:6]}")
        os.makedirs(self.temp_video_dir, exist_ok=True)
        self.playwright = None
        self.browser = None
        self.context = None

    async def start(self):
        from playwright.async_api import async_playwright
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-web-security",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
            ]
        )
        self.context = await self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_dir=self.temp_video_dir,
            record_video_size={"width": 1920, "height": 1080},
        )
        log_info("[PlaywrightRenderer] Shared browser context started.")

    async def record_scene(self, html_content: str, timeline_data: Dict, scene_id: str) -> Optional[str]:
        temp_html = os.path.join(self.temp_video_dir, f"{scene_id}.html")
        with open(temp_html, "w", encoding="utf-8") as f:
            f.write(html_content)

        page = await self.context.new_page()
        try:
            await page.add_init_script(f"window.TIMELINE_DATA = {json.dumps(timeline_data)};")
            await page.add_init_script("window.IS_CAPTURING = true;")
            await page.add_init_script("window.PLAYWRIGHT_START_TIME = Date.now();")

            page.on("pageerror", lambda err: log_error(f"[BrowserJSError] {scene_id}: {err}"))
            page.on("console", lambda msg: (
                log_warning(f"[BrowserConsole] {scene_id}: {msg.text}") 
                if msg.type == "error" else None
            ))

            await page.add_init_script("""
                window.__JS_ERRORS__ = [];
                window.addEventListener('error', function(e) {
                    window.__JS_ERRORS__.push(e.message + ' at ' + e.filename + ':' + e.lineno);
                });
                window.addEventListener('unhandledrejection', function(e) {
                    window.__JS_ERRORS__.push('Promise: ' + e.reason);
                });
            """)

            abs_html = os.path.abspath(temp_html).replace("\\", "/")
            await page.goto(f"file:///{abs_html}", wait_until="networkidle", timeout=20000)

            # Wait for fonts
            try:
                await page.wait_for_function("document.fonts.check('700 18px Playfair Display')", timeout=5000)
            except Exception:
                pass

            scene_duration_ms = timeline_data.get("total_duration_ms") or 45000
            # UPGRADE 7: dynamic timeout = audio duration + 15s, clamped [60s, 180s]
            timeout_ms = min(180000, max(60000, int(scene_duration_ms) + 15000))


            log_info(f"[PlaywrightRenderer] Recording {scene_id} in Virtual Time Mode...")
            try:
                await page.wait_for_function(
                    "window.SCENE_FINISHED === true",
                    timeout=timeout_ms
                )
                log_info(f"[PlaywrightRenderer] Scene {scene_id} finished naturally.")
            except Exception as timeout_err:
                log_warning(
                    f"[PlaywrightRenderer] Scene {scene_id} timed out after {timeout_ms}ms. "
                    f"Forcing finish and saving partial capture."
                )
                # Check if the page is still responsive
                try:
                    # Force set the flag
                    await page.evaluate("window.SCENE_FINISHED = true;")
                    # Also try to capture any JS errors that caused the timeout
                    js_errors = await page.evaluate("""
                        () => window.__JS_ERRORS__ ? window.__JS_ERRORS__.join('|') : 'none'
                    """)
                    if js_errors and js_errors != 'none':
                        log_error(f"[PlaywrightRenderer] JS errors in {scene_id}: {js_errors}")
                    await asyncio.sleep(1.0)
                except Exception as force_err:
                    log_error(f"[PlaywrightRenderer] Could not force finish: {force_err}")

            # Get video path and close page to save file
            delay_ms = 0
            try:
                delay_ms = await page.evaluate("window.RECORDING_DELAY_MS || 0")
            except Exception as e:
                log_error(f"[PlaywrightRenderer] Failed to evaluate window.RECORDING_DELAY_MS: {e}")

            if page.video:
                video_path = await page.video.path()
            else:
                video_path = None
            await page.close()

            if not video_path:
                raise Exception("No video recording context found on the page.")

            # PRIORITY 3 FIX: Ensure Playwright Chromium has completely flushed & released the video file handle
            file_released = False
            for attempt in range(40):  # Wait up to 10 seconds for Chromium to flush & unlock
                if os.path.exists(video_path):
                    try:
                        s1 = os.path.getsize(video_path)
                        await asyncio.sleep(0.25)
                        s2 = os.path.getsize(video_path)
                        if s1 > 0 and s1 == s2:
                            # Test exclusive lock access
                            with open(video_path, "rb+"):
                                pass
                            file_released = True
                            break
                    except (PermissionError, OSError):
                        pass
                await asyncio.sleep(0.25)

            if not file_released:
                log_warning(f"[PlaywrightRenderer] Warning: {video_path} still locked after waiting. Attempting fallback move/copy.")

            # Move video to destination with retries for Windows file lock (WinError 32)
            dst = os.path.join(self.output_dir, f"{scene_id}_raw.webm")
            if os.path.exists(dst):
                try:
                    os.remove(dst)
                except Exception:
                    pass

            moved = False
            for attempt in range(40):
                try:
                    shutil.move(video_path, dst)
                    moved = True
                    break
                except (PermissionError, OSError):
                    await asyncio.sleep(0.25)
                except Exception as e:
                    log_error(f"[PlaywrightRenderer] Error moving video (attempt {attempt}): {e}")
                    await asyncio.sleep(0.25)

            if not moved:
                log_info("[PlaywrightRenderer] shutil.move failed (file locked). Trying shutil.copy fallback...")
                for attempt in range(40):
                    try:
                        shutil.copy2(video_path, dst)
                        moved = True
                        break
                    except (PermissionError, OSError):
                        await asyncio.sleep(0.25)

                if moved:
                    for _ in range(20):
                        try:
                            os.remove(video_path)
                            break
                        except Exception:
                            await asyncio.sleep(0.25)
                else:
                    raise Exception(f"Failed to copy/move video file from {video_path} to {dst} after retries (WinError 32).")

            # Write companion JSON for delay seeking
            if moved:
                dst_json = dst.replace(".webm", ".json")
                try:
                    with open(dst_json, "w", encoding="utf-8") as f:
                        json.dump({"delay_ms": delay_ms}, f)
                    log_info(f"[PlaywrightRenderer] Saved scene delay metadata ({delay_ms}ms): {dst_json}")
                except Exception as e:
                    log_error(f"[PlaywrightRenderer] Failed to write delay JSON: {e}")

            log_info(f"[PlaywrightRenderer] Scene {scene_id} recorded and saved to: {dst}")
            return dst

        except Exception as e:
            log_error(f"[PlaywrightRenderer] Failed recording {scene_id}: {e}")
            try:
                await page.close()
            except Exception:
                pass
            return None

    async def close(self):
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception as e:
            log_error(f"[PlaywrightRenderer] Error during shutdown: {e}")
        shutil.rmtree(self.temp_video_dir, ignore_errors=True)


class PlaywrightRenderManager:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self.loop = None
        self.thread = None
        self.renderer = None
        self._started = False
        self._lock = None

    def start(self):
        self._started_event = threading.Event()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        self._started_event.wait()
        if not self._started:
            raise RuntimeError("PlaywrightRenderManager failed to start. Check server logs for browser initialization errors.")

    def _run_loop(self):
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        async def _init():
            try:
                self.renderer = PlaywrightRenderer(self.output_dir)
                await self.renderer.start()
                self._lock = asyncio.Lock()
                self._started = True
            except Exception as e:
                log_error(f"[PlaywrightRenderManager] Failed to initialize Playwright: {e}")
                self._started = False
            finally:
                self._started_event.set()

        self.loop.run_until_complete(_init())
        self.loop.run_forever()

    async def _record_scene_internal(self, html_content: str, timeline_data: Dict, scene_id: str) -> Optional[str]:
        async with self._lock:
            return await self.renderer.record_scene(html_content, timeline_data, scene_id)

    async def record_scene_async(self, html_content: str, timeline_data: Dict, scene_id: str) -> Optional[str]:
        future = asyncio.run_coroutine_threadsafe(
            self._record_scene_internal(html_content, timeline_data, scene_id),
            self.loop
        )
        return await asyncio.wrap_future(future)

    def shutdown(self):
        if self.loop:
            async def _cleanup():
                if self.renderer:
                    try:
                        await self.renderer.close()
                    except Exception as e:
                        log_error(f"[PlaywrightRenderManager] Error closing renderer: {e}")
                self.loop.stop()
            asyncio.run_coroutine_threadsafe(_cleanup(), self.loop)
            self.thread.join(timeout=5)


# ─────────────────────────────────────────────────────────────────────
# Backward compatibility standalones (launches a fresh browser context)
# ─────────────────────────────────────────────────────────────────────

def record_scene_video(
    html_content: str,
    timeline_data: Dict,
    total_duration_ms: float,
    output_dir: str,
    scene_id: str,
) -> Optional[str]:
    """
    Legacy fallback: launches browser on every call.
    """
    result_container = [None]
    error_container = [None]

    def _run_in_thread():
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

        async def _capture():
            from playwright.async_api import async_playwright
            temp_video_dir = os.path.join(output_dir, f"pw_{uuid.uuid4().hex[:6]}")
            os.makedirs(temp_video_dir, exist_ok=True)
            temp_html = os.path.join(temp_video_dir, "scene.html")
            with open(temp_html, "w", encoding="utf-8") as f:
                f.write(html_content)

            try:
                async with async_playwright() as p:
                    browser = await p.chromium.launch(
                        headless=True,
                        args=["--disable-web-security", "--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
                    )
                    context = await browser.new_context(
                        viewport={"width": 1920, "height": 1080},
                        record_video_dir=temp_video_dir,
                        record_video_size={"width": 1920, "height": 1080},
                    )
                    page = await context.new_page()
                    await page.add_init_script(f"window.TIMELINE_DATA = {json.dumps(timeline_data)};")
                    await page.add_init_script("window.IS_CAPTURING = true;")
                    await page.add_init_script("window.PLAYWRIGHT_START_TIME = Date.now();")

                    page.on("pageerror", lambda err: log_error(f"[BrowserJSError] {scene_id}: {err}"))
                    page.on("console", lambda msg: (
                        log_warning(f"[BrowserConsole] {scene_id}: {msg.text}")
                        if msg.type == "error" else None
                    ))
                    await page.add_init_script("""
                        window.__JS_ERRORS__ = [];
                        window.addEventListener('error', function(e) {
                            window.__JS_ERRORS__.push(e.message + ' at ' + e.filename + ':' + e.lineno);
                        });
                        window.addEventListener('unhandledrejection', function(e) {
                            window.__JS_ERRORS__.push('Promise: ' + e.reason);
                        });
                    """)

                    abs_html = os.path.abspath(temp_html).replace("\\", "/")
                    await page.goto(f"file:///{abs_html}", wait_until="networkidle", timeout=20000)

                    try:
                        await page.wait_for_function("document.fonts.check('700 18px Playfair Display')", timeout=5000)
                    except Exception:
                        pass

                    # Wait for finished flag
                    timeout_ms = min(420000, max(90000, int(total_duration_ms) + 25000))
                    try:
                        await page.wait_for_function("window.SCENE_FINISHED === true", timeout=timeout_ms)
                        log_info(f"[Playwright legacy] Scene {scene_id} finished naturally.")
                    except Exception:
                        log_warning(f"[Playwright legacy] Scene {scene_id} timed out. Forcing finish.")
                        try:
                            await page.evaluate("window.SCENE_FINISHED = true;")
                            js_errors = await page.evaluate(
                                "() => window.__JS_ERRORS__ ? window.__JS_ERRORS__.join('|') : 'none'"
                            )
                            if js_errors and js_errors != 'none':
                                log_error(f"[Playwright legacy] JS errors in {scene_id}: {js_errors}")
                            await asyncio.sleep(1.0)
                        except Exception:
                            pass

                    delay_ms = 0
                    try:
                        delay_ms = await page.evaluate("window.RECORDING_DELAY_MS || 0")
                    except Exception:
                        pass

                    await context.close()
                    await browser.close()
            except Exception as e:
                error_container[0] = e
                shutil.rmtree(temp_video_dir, ignore_errors=True)
                return None

            # Wait for Chromium to flush the WebM file (Windows file handle release delay)
            time.sleep(0.3)

            # Wait up to 5s for the .webm file to appear and have content
            webm_files = []
            for _ in range(50):
                webm_files = [f for f in os.listdir(temp_video_dir) if f.endswith(".webm")]
                if webm_files:
                    src_candidate = os.path.join(temp_video_dir, webm_files[0])
                    if os.path.getsize(src_candidate) > 0:
                        break
                time.sleep(0.1)

            if not webm_files:
                error_container[0] = Exception(f"No .webm produced for {scene_id}")
                shutil.rmtree(temp_video_dir, ignore_errors=True)
                return None

            src = os.path.join(temp_video_dir, webm_files[0])
            dst = os.path.join(output_dir, f"{scene_id}_raw.webm")
            if os.path.exists(dst):
                try:
                    os.remove(dst)
                except Exception:
                    pass

            # Retry move with copy fallback for Windows file locks (WinError 32)
            moved = False
            for attempt in range(50):
                try:
                    shutil.move(src, dst)
                    moved = True
                    break
                except (PermissionError, OSError):
                    time.sleep(0.1)

            if not moved:
                # Fallback: copy instead of move
                for attempt in range(50):
                    try:
                        shutil.copy2(src, dst)
                        moved = True
                        break
                    except (PermissionError, OSError):
                        time.sleep(0.1)

            if not moved:
                error_container[0] = Exception(f"Failed to move/copy WebM for {scene_id} (WinError 32)")
                return None

            # Write companion JSON for delay seeking
            if moved:
                dst_json = dst.replace(".webm", ".json")
                try:
                    with open(dst_json, "w", encoding="utf-8") as f:
                        json.dump({"delay_ms": delay_ms}, f)
                except Exception:
                    pass

            shutil.rmtree(temp_video_dir, ignore_errors=True)
            return dst

        result_container[0] = asyncio.run(_capture())

    t = threading.Thread(target=_run_in_thread, daemon=True)
    t.start()
    t.join()

    if error_container[0]:
        log_error(f"[Playwright legacy] Failed for {scene_id}: {error_container[0]}")
        return None
    return result_container[0]


def render_all_scenes(scenes: list, output_dir: str) -> list:
    """
    Legacy fallback for parallel scene render.
    """
    result_container = [None]

    def _run_in_thread():
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

        async def _capture_all():
            manager = PlaywrightRenderManager(output_dir)
            manager.start()
            
            async def _render_single(idx: int, scene: Dict):
                html_content = scene.get("html_content", "")
                timeline_data = scene.get("timeline_data", {})
                scene_id = scene.get("scene_id", f"scene_{idx}")
                return await manager.record_scene_async(html_content, timeline_data, scene_id)

            tasks = []
            for i, scene in enumerate(scenes):
                tasks.append(asyncio.create_task(_render_single(i, scene)))

            res = await asyncio.gather(*tasks, return_exceptions=False)
            manager.shutdown()
            return res

        result_container[0] = asyncio.run(_capture_all())

    t = threading.Thread(target=_run_in_thread, daemon=True)
    t.start()
    t.join()
    return result_container[0]
