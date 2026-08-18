import os
import time
import base64
import httpx
import asyncio
from app.utils.logger import log_info, log_error

class KaggleCloudClient:
    """
    Handles communication with the Kaggle MuseTalk Cloud Engine via Ngrok.
    Implements base64 encoding, sequential queueing, and timing instrumentation.
    """
    # Global semaphore ensuring only ONE request hits the remote Kaggle GPU at a time
    _semaphore = asyncio.Semaphore(1)
    
    def __init__(self, ngrok_url: str):
        self.base_url = ngrok_url.strip().rstrip('/')
        self.timeout = 300.0  # 5 minutes for heavy lipsync processing
        self.max_retries = 3
        log_info(f"[Kaggle Client] Initialized with Base URL: '{self.base_url}'")

    async def check_health(self) -> dict:
        """Ping the Kaggle notebook to ensure it is awake."""
        url = f"{self.base_url}/health"
        log_info(f"[Kaggle Client] Pinging health endpoint: {url}")
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, timeout=15.0)
                resp.raise_for_status()
                data = resp.json()
                gpu = data.get('gpu') or data.get('gpu_name') or "Unknown"
                log_info(f"[Kaggle Client] Health Check OK: GPU={gpu}")
                return data
        except Exception as e:
            log_error(f"[Kaggle Client] Health Check Failed: {e}")
            return {"status": "offline", "error": str(e)}

    async def clear_cache(self) -> bool:
        """Clear CUDA VRAM on Kaggle if OOM errors occur."""
        url = f"{self.base_url}/clear_cache"
        log_info(f"[Kaggle Client] Requesting remote VRAM clearing: {url}")
        try:
            async with httpx.AsyncClient() as client:
                await client.get(url, timeout=15.0)
                log_info("[Kaggle Client] Cleared GPU Cache successfully")
                return True
        except Exception as e:
            log_error(f"[Kaggle Client] Failed to clear cache: {e}")
            return False

    async def generate_lipsync(
        self, 
        scene_id: str, 
        audio_path: str, 
        avatar_image_path: str = None
    ) -> str:
        """
        Send audio (+ optional avatar image) to Kaggle for MuseTalk lipsync.
        Enforces sequential execution via _semaphore(1) and instruments sub-step timings.
        """
        url = f"{self.base_url}/generate_lipsync"
        log_info(f"[Kaggle Client] Enqueuing lipsync task for scene: {scene_id}")

        async with self._semaphore:
            t_start = time.time()
            log_info(f"[Kaggle Client] Starting lipsync task execution for scene: {scene_id}")
            log_info(f"[Kaggle Client] Raw input audio: {audio_path}")
            
            # 1. Encode Audio — Convert MP3→WAV first (Wav2Lip requires WAV)
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"Audio file not found: {audio_path}")
            
            wav_path = audio_path.replace(".mp3", ".wav")
            if audio_path.endswith(".mp3") and not os.path.exists(wav_path):
                import subprocess
                def _run_ffmpeg():
                    return subprocess.run(
                        ["ffmpeg", "-y", "-i", audio_path, "-ar", "16000", "-ac", "1", wav_path],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                res = await asyncio.to_thread(_run_ffmpeg)
                if res.returncode != 0:
                    log_error(f"[Kaggle Client] FFmpeg conversion failed: {res.stderr.decode('utf-8', errors='ignore')}")
                else:
                    log_info(f"[Kaggle Client] WAV conversion complete: {wav_path}")
            
            final_audio_path = wav_path if os.path.exists(wav_path) else audio_path
                
            with open(final_audio_path, "rb") as f:
                audio_data = f.read()
                audio_b64 = base64.b64encode(audio_data).decode('utf-8')
                
            # 2. Encode Image
            from app.config import settings
            fallback_avatar = settings.AVATAR_IMAGE_PATH if (settings.AVATAR_IMAGE_PATH and os.path.exists(settings.AVATAR_IMAGE_PATH)) else "static/avatars/my_avatar.jpg"
            resolved_avatar = avatar_image_path if (avatar_image_path and os.path.exists(avatar_image_path)) else fallback_avatar
            
            avatar_b64 = None
            if os.path.exists(resolved_avatar):
                try:
                    from PIL import Image
                    with Image.open(resolved_avatar) as img:
                        pass
                except Exception as e:
                    log_error(f"[Kaggle Client] Image check warning: {e}")
                    
                with open(resolved_avatar, "rb") as f:
                    img_data = f.read()
                    avatar_b64 = base64.b64encode(img_data).decode('utf-8')
            
            if not avatar_b64:
                log_error("[Kaggle Client] No avatar image found — lipsync will be skipped.")
                return None
                    
            payload = {
                "scene_id": scene_id,
                "audio_base64": audio_b64,
                "avatar_image_base64": avatar_b64
            }
            
            t_encoded = time.time()
            t_encode_dur = t_encoded - t_start

            # 3. Request with Retries and Instrumentation
            for attempt in range(self.max_retries):
                try:
                    log_info(f"[Kaggle Client] Requesting lipsync for {scene_id} (Attempt {attempt+1}/{self.max_retries})...")
                    t_req_start = time.time()
                    
                    async with httpx.AsyncClient() as client:
                        resp = await client.post(url, json=payload, timeout=self.timeout)
                        t_req_done = time.time()
                        t_remote_gpu = t_req_done - t_req_start
                        
                        log_info(f"[Kaggle Client] Remote rendering finished in {t_remote_gpu:.2f}s | HTTP Status: {resp.status_code}")
                        
                        if resp.status_code != 200:
                            error_body = resp.text[:1000]
                            log_error(f"[Kaggle Client] Server Error {resp.status_code}: {error_body}")
                            if "CUDA out of memory" in error_body:
                                log_error("[Kaggle Client] Kaggle OOM! Clearing remote GPU cache and retrying...")
                                await self.clear_cache()
                                await asyncio.sleep(5)
                                continue
                            resp.raise_for_status()
                        
                        data = resp.json()
                        if data.get("status") != "success":
                            raise Exception(data.get("error_message", "Unknown Kaggle error"))
                            
                        # Decode and save Video payload
                        t_save_start = time.time()
                        video_b64 = data.get("lipsync_video_base64")
                        output_path = audio_path.replace("_audio.mp3", "_lipsync.mp4")
                        
                        with open(output_path, "wb") as f:
                            f.write(base64.b64decode(video_b64))
                            
                        t_save_done = time.time()
                        t_save_dur = t_save_done - t_save_start
                        t_total_dur = t_save_done - t_start

                        # TIMING INSTRUMENTATION LOG SUMMARY
                        log_info(
                            f"[Kaggle Timing Summary] {scene_id}: "
                            f"Encode={t_encode_dur:.2f}s | Remote GPU={t_remote_gpu:.2f}s | "
                            f"Download & Save={t_save_dur:.2f}s | Total={t_total_dur:.2f}s"
                        )
                        return output_path
                        
                except httpx.RequestError as e:
                    log_error(f"[Kaggle Client] Network error on {scene_id}: {e}")
                    if attempt < self.max_retries - 1:
                        backoff = (attempt + 1) * 5
                        log_info(f"[Kaggle Client] Backoff sleeping {backoff}s before retry...")
                        await asyncio.sleep(backoff)
                    else:
                        raise Exception(f"Kaggle request failed for {scene_id}: {e}")
                except Exception as e:
                    log_error(f"[Kaggle Client] Error on attempt {attempt+1}: {e}")
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(5)
                    else:
                        raise e
            return None
