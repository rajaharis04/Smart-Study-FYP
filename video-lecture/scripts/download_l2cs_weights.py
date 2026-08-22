"""
download_l2cs_weights.py — Fetch the L2CS-Net Gaze360 pretrained weights.

The Attention Monitor's PRECISE gaze estimator (video-lecture/modules/
attention_monitor/gaze.py) uses L2CS-Net, which needs a pretrained weight file
(`L2CSNet_gaze360.pkl`, ResNet50 backbone). Those weights are NOT committed to
the repo (large binary + licensing) — this script downloads them into the
expected location so gaze works out of the box.

Where it lands (matches config.GAZE_WEIGHTS_PATH default):
    video-lecture/external/L2CS-Net/models/L2CSNet_gaze360.pkl

Usage (from the repo root, inside the CV virtualenv):
    python video-lecture/scripts/download_l2cs_weights.py
    python video-lecture/scripts/download_l2cs_weights.py --dest <path> --url <url>

Notes
-----
• The official weights live on the L2CS-Net authors' Google Drive (see their
  README). Direct-download URLs rot over time, so this script:
    1. tries a list of known public mirrors (overridable with --url),
    2. otherwise prints clear manual-download instructions and exits 0 so it
       never breaks an automated setup — gaze simply falls back to the free
       MediaPipe iris gaze until the weights are present.
• If `gdown` is installed we use it (handles Google-Drive confirm tokens);
  otherwise we fall back to a plain urllib download for direct URLs.
"""
from __future__ import annotations

import argparse
import os
import sys

# scripts/ → video-lecture/ → <repo root>
_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))

DEFAULT_DEST = os.path.join(
    _REPO_ROOT, "video-lecture", "external", "L2CS-Net", "models", "L2CSNet_gaze360.pkl"
)

# Known public sources for the Gaze360 ResNet50 checkpoint. The Google-Drive id
# is the one referenced by the L2CS-Net project; mirrors may change over time.
GDRIVE_FILE_ID = "18S956r4jnHtSeT8z8t3z8AtJVjs1kJfM"
CANDIDATE_URLS = [
    # HuggingFace community mirror (direct download — preferred when reachable).
    "https://huggingface.co/carumaster/L2CS-Net/resolve/main/L2CSNet_gaze360.pkl",
]

MANUAL_INSTRUCTIONS = f"""
────────────────────────────────────────────────────────────────────────────
Could not auto-download the L2CS-Net weights. This is NOT fatal — the Attention
Monitor keeps working using the free MediaPipe iris gaze until the weights are
present. To enable the precise L2CS-Net gaze, download the file manually:

  1. Open the L2CS-Net repo README:  https://github.com/Ahmednull/L2CS-Net
     and grab the "Gaze360" ResNet50 checkpoint (L2CSNet_gaze360.pkl),
     or the Google-Drive file id: {GDRIVE_FILE_ID}
  2. Save it to EXACTLY this path:
        {DEFAULT_DEST}
  3. Restart the backend. Verify at:  GET /api/attention/status
        → "gaze_available": true
────────────────────────────────────────────────────────────────────────────
"""


def _ensure_parent_dir(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)


def _already_present(dest: str) -> bool:
    # A valid checkpoint is well over 1 MB; guard against a truncated/HTML file.
    return os.path.exists(dest) and os.path.getsize(dest) > 1_000_000


def _try_gdown(dest: str) -> bool:
    try:
        import gdown  # type: ignore
    except Exception:
        return False
    try:
        print(f"→ Trying gdown (Google Drive id {GDRIVE_FILE_ID}) …")
        gdown.download(id=GDRIVE_FILE_ID, output=dest, quiet=False)
        return _already_present(dest)
    except Exception as exc:
        print(f"  gdown failed: {exc}")
        return False


def _try_urllib(url: str, dest: str) -> bool:
    import urllib.request

    try:
        print(f"→ Downloading: {url}")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as resp, open(dest, "wb") as out:
            total = 0
            while True:
                chunk = resp.read(1 << 16)
                if not chunk:
                    break
                out.write(chunk)
                total += len(chunk)
        ok = _already_present(dest)
        if not ok:
            print(f"  downloaded only {total} bytes — looks invalid, discarding.")
            try:
                os.remove(dest)
            except OSError:
                pass
        return ok
    except Exception as exc:
        print(f"  download failed: {exc}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Download L2CS-Net Gaze360 weights.")
    parser.add_argument("--dest", default=DEFAULT_DEST, help="Output .pkl path.")
    parser.add_argument("--url", default=None, help="Explicit direct-download URL.")
    parser.add_argument("--force", action="store_true", help="Re-download even if present.")
    args = parser.parse_args()

    dest = os.path.abspath(args.dest)

    if _already_present(dest) and not args.force:
        print(f"✅ Weights already present: {dest}")
        return 0

    _ensure_parent_dir(dest)

    urls = [args.url] if args.url else list(CANDIDATE_URLS)

    # 1) Explicit / mirror URLs via urllib.
    for url in urls:
        if url and _try_urllib(url, dest):
            print(f"✅ Saved weights → {dest}")
            return 0

    # 2) gdown (handles Google-Drive confirm tokens) as a fallback.
    if _try_gdown(dest):
        print(f"✅ Saved weights → {dest}")
        return 0

    # 3) Give clear manual steps; exit 0 so setup scripts don't hard-fail.
    print(MANUAL_INSTRUCTIONS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
