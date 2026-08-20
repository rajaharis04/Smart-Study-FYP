"""
verify_webcam_loop.py — Local webcam end-to-end verification harness.

Purpose (spec §8.3f): run the WHOLE attention pipeline on a local webcam so
you can eyeball that landmarks, EAR, head-pose, (optional) gaze, recognition,
and the session Present/Absent decision all behave — WITHOUT the FastAPI/DB
layer. This is a developer tool, not part of the served app.

What it does:
  1. Opens the default webcam (cv2.VideoCapture(0)).
  2. Optionally ENROLLS you first (captures ENROLL photos → ArcFace embedding),
     then runs the session with live recognition.
  3. Samples ~1 frame/second, runs `scorer.analyze_frame`, feeds a
     `SessionAggregator`, and prints per-frame metrics live.
  4. On quit ('q') or after --seconds, prints the final SessionResult
     (attention_ratio, Present/Absent, flags).

Privacy: frames are shown in a local preview window for your convenience but
are NEVER written to disk. Nothing is persisted anywhere.

Usage (from the repo root, inside the CV virtualenv):
    python video-lecture/scripts/verify_webcam_loop.py
    python video-lecture/scripts/verify_webcam_loop.py --enroll --seconds 60
    python video-lecture/scripts/verify_webcam_loop.py --no-preview
"""
from __future__ import annotations

import os
import sys
import time
import argparse

# ── Make the pure CV package importable when run as a plain script ──────────
# scripts/ → video-lecture/ → modules/
_HERE = os.path.dirname(os.path.abspath(__file__))
_MODULES_DIR = os.path.abspath(os.path.join(_HERE, "..", "modules"))
if _MODULES_DIR not in sys.path:
    sys.path.insert(0, _MODULES_DIR)

# Windows consoles default to cp1252, which can't encode Unicode box-drawing
# chars and crashes with UnicodeEncodeError. Force UTF-8 (with a safe fallback)
# so this dev tool prints cleanly on any terminal.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import cv2  # noqa: E402
import numpy as np  # noqa: E402


from attention_monitor import config  # noqa: E402
from attention_monitor import scorer, recognition  # noqa: E402
from attention_monitor.landmarks import FaceMeshDetector  # noqa: E402
from attention_monitor.gaze import get_default_estimator  # noqa: E402


# ══════════════════════════════════════════════════════════════════════════
#  Enrollment (optional)
# ══════════════════════════════════════════════════════════════════════════

def run_enrollment(cap, num_photos: int) -> dict:
    """Capture `num_photos` frames and build an embedding for 'student 1'.

    Returns an {student_id: embedding} dict suitable for `analyze_frame`.
    Press SPACE to capture each photo, 'q' to abort enrolment.
    """
    print(f"\n=== ENROLLMENT: capture {num_photos} photos ===")
    print("Look at the camera. Press SPACE to capture each shot, 'q' to skip.\n")

    shots: list[np.ndarray] = []
    while len(shots) < num_photos:
        ok, frame = cap.read()
        if not ok:
            print("!! Camera read failed during enrolment.")
            break

        preview = frame.copy()
        cv2.putText(
            preview,
            f"Enroll {len(shots)}/{num_photos} - SPACE=capture q=skip",
            (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2,
        )
        cv2.imshow("Attention Monitor - Enrollment", preview)
        key = cv2.waitKey(1) & 0xFF
        if key == ord(" "):
            shots.append(frame.copy())
            print(f"  captured {len(shots)}/{num_photos}")
        elif key == ord("q"):
            print("  enrolment skipped by user.")
            break

    cv2.destroyWindow("Attention Monitor - Enrollment")

    if len(shots) < config.ENROLL_MIN_PHOTOS:
        print(f"  not enough photos ({len(shots)}); continuing WITHOUT recognition.")
        return {}

    try:
        embedding = recognition.build_enrollment_embedding(shots)
    except recognition.EnrollmentError as exc:
        print(f"  enrolment failed: {exc}. Continuing WITHOUT recognition.")
        return {}
    finally:
        for s in shots:
            del s

    print("  ✅ enrolled as student_id=1\n")
    return {1: embedding}


# ══════════════════════════════════════════════════════════════════════════
#  Main monitoring loop
# ══════════════════════════════════════════════════════════════════════════

def main() -> int:
    parser = argparse.ArgumentParser(description="Local webcam attention pipeline test.")
    parser.add_argument("--camera", type=int, default=0, help="Webcam index (default 0).")
    parser.add_argument("--seconds", type=int, default=0,
                        help="Auto-stop after N seconds (0 = until 'q').")
    parser.add_argument("--enroll", action="store_true",
                        help="Run enrolment first, then monitor with recognition.")
    parser.add_argument("--photos", type=int, default=config.ENROLL_MAX_PHOTOS,
                        help="Photos to capture during enrolment.")
    parser.add_argument("--no-preview", action="store_true",
                        help="Disable the live preview window (headless).")
    args = parser.parse_args()

    print("=" * 60)
    print("   Attention & Presence Monitor - Local Webcam Verify")
    print("=" * 60)
    print("Effective config:")

    for k, v in config.as_dict().items():
        print(f"  {k:32s} = {v}")
    print()

    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        print(f"!! Could not open webcam index {args.camera}.")
        return 1

    # Optional enrolment
    enrolled: dict = {}
    if args.enroll:
        enrolled = run_enrollment(cap, args.photos)

    detector = FaceMeshDetector()
    gaze = get_default_estimator()
    if config.ENABLE_GAZE:
        print(f"Gaze enabled → available={gaze.available} "
              f"(error: {gaze.load_error})\n")

    aggregator = scorer.SessionAggregator(
        expected_student_id=(1 if enrolled else None)
    )

    interval = config.SAMPLE_INTERVAL_SECONDS
    start_time = time.time()
    last_sample = 0.0
    sample_count = 0

    print(f"Sampling every {interval:.2f}s (~{config.SAMPLE_FPS} fps). "
          "Press 'q' in the preview window to finish.\n")


    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("!! Camera read failed.")
                break

            now = time.time()
            do_sample = (now - last_sample) >= interval

            if do_sample:
                last_sample = now
                sample_count += 1

                fr = scorer.analyze_frame(
                    frame,
                    detector,
                    gaze_estimator=gaze,
                    enrolled=enrolled or None,
                )
                aggregator.add(fr)

                status_word = "ATTENTIVE" if fr.is_attentive else "---------"
                ident = ""
                if fr.identity_checked:
                    ident = (f" | id={fr.matched_student_id} "
                             f"sim={fr.identity_similarity:.2f} "
                             f"{'MATCH' if fr.identity_matched else 'nomatch'}")
                print(
                    f"[{sample_count:03d}] {status_word} "
                    f"faces={fr.face_count} "
                    f"EAR={fr.ear:.3f}({'open' if fr.eyes_open else 'shut'}) "
                    f"yaw={fr.yaw_deg:+.1f} pitch={fr.pitch_deg:+.1f} "
                    f"frontal={fr.head_frontal} "
                    f"ratio={aggregator.snapshot_ratio():.2f}"
                    f"{ident}"
                )

            # Live preview (optional)
            if not args.no_preview:
                preview = frame.copy()
                ratio = aggregator.snapshot_ratio()
                cv2.putText(preview, f"samples={sample_count} ratio={ratio:.2f}",
                            (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                cv2.putText(preview, "press 'q' to finish",
                            (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
                cv2.imshow("Attention Monitor - Live", preview)
                if (cv2.waitKey(1) & 0xFF) == ord("q"):
                    break

            if args.seconds and (now - start_time) >= args.seconds:
                print(f"\nReached --seconds={args.seconds}; stopping.")
                break
    except KeyboardInterrupt:
        print("\nInterrupted by user (Ctrl-C).")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        detector.close()

    # ── Final verdict ─────────────────────────────────────────────────
    result = aggregator.finalize()
    print("\n" + "=" * 60)
    print("                    SESSION RESULT")
    print("=" * 60)

    for k, v in result.to_dict().items():
        print(f"  {k:24s} = {v}")
    print()
    print(f"  DECISION: {result.status}  "
          f"(threshold = {config.ATTENDANCE_THRESHOLD:.2f})")
    if result.flags:
        print(f"  FLAGS RAISED: {', '.join(result.flags)}")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
