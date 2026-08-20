"""
recognition.py — Face identity via DeepFace (ArcFace backend).

Single responsibility: turn a face image into a 512-d ArcFace embedding, and
compare embeddings with cosine similarity. This is how we answer spec §2 Q1
("Who is watching?").

This module is deliberately **DB-independent** (per your decision #1):
  • `embed_face()` / `embed_faces()` produce embeddings from in-memory frames.
  • `cosine_similarity()` / `match_embedding()` compare a probe against a set
    of enrolled embeddings.
The API/persistence layer (admin_web/backend/app/api/attention.py) is what
stores the returned embeddings into Postgres and calls `match_embedding()`.

Privacy (§6, hard rule): images passed in are processed in-memory only. This
module never writes an image to disk. DeepFace is invoked with
`enforce_detection` handling so a frame with no face raises a clean, typed
error instead of crashing the request.

Attribution: DeepFace (https://github.com/serengil/deepface) — MIT License.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np

from . import config


# ══════════════════════════════════════════════════════════════════════════
#  Errors
# ══════════════════════════════════════════════════════════════════════════

class NoFaceDetected(Exception):
    """Raised when DeepFace cannot find a face in the supplied image."""


class EnrollmentError(Exception):
    """Raised when enrolment inputs are invalid (e.g. too few usable photos)."""


# ══════════════════════════════════════════════════════════════════════════
#  Result containers
# ══════════════════════════════════════════════════════════════════════════

@dataclass
class MatchResult:
    """Outcome of matching a probe embedding against enrolled identities.

    matched_id : the enrolled key (student_id) of the best match, or None.
    similarity : cosine similarity of the best match (0..1).
    is_match   : True iff similarity >= configured threshold.
    """

    matched_id: Optional[int]
    similarity: float
    is_match: bool


# ══════════════════════════════════════════════════════════════════════════
#  Embedding generation (DeepFace / ArcFace)
# ══════════════════════════════════════════════════════════════════════════

def embed_face(
    image_bgr: np.ndarray,
    *,
    enforce_detection: bool = True,
) -> np.ndarray:
    """Compute a single L2-normalized ArcFace embedding for a face image.

    Parameters
    ----------
    image_bgr : np.ndarray
        Decoded BGR frame containing (ideally) exactly one face.
    enforce_detection : bool
        If True (default), raise `NoFaceDetected` when no face is found. During
        continuous monitoring we set this False to tolerate transient misses.

    Returns
    -------
    np.ndarray
        A 1-D float32 vector of length `RECOGNITION_EMBEDDING_DIM`, L2-normalized
        so cosine similarity reduces to a dot product.
    """
    # Lazy import: DeepFace pulls in TensorFlow (~heavy). Importing inside the
    # function keeps `import recognition` cheap and avoids loading TF unless we
    # actually run recognition.
    from deepface import DeepFace

    try:
        representations = DeepFace.represent(
            img_path=image_bgr,  # DeepFace accepts a numpy BGR array directly
            model_name=config.RECOGNITION_MODEL_NAME,
            detector_backend=config.RECOGNITION_DETECTOR_BACKEND,
            enforce_detection=enforce_detection,
            align=True,
        )
    except ValueError as exc:
        # DeepFace raises ValueError("Face could not be detected...") when
        # enforce_detection=True and nothing is found. Normalize to our type.
        raise NoFaceDetected(str(exc)) from exc

    if not representations:
        raise NoFaceDetected("DeepFace returned no representations.")

    # When multiple faces are present DeepFace returns several; for embedding we
    # take the first (largest) — multi-face *policing* is the scorer's job.
    embedding = np.asarray(representations[0]["embedding"], dtype=np.float32)
    return _l2_normalize(embedding)


def embed_faces(
    images_bgr: List[np.ndarray],
    *,
    enforce_detection: bool = True,
) -> List[np.ndarray]:
    """Embed a list of images, skipping ones with no detectable face.

    Used by enrolment (3-5 reference photos). Returns only the embeddings that
    succeeded; the caller checks the count against ENROLL_MIN_PHOTOS.
    """
    embeddings: List[np.ndarray] = []
    for img in images_bgr:
        try:
            embeddings.append(embed_face(img, enforce_detection=enforce_detection))
        except NoFaceDetected:
            # Skip unusable photos; do not abort the whole enrolment.
            continue
    return embeddings


def build_enrollment_embedding(images_bgr: List[np.ndarray]) -> np.ndarray:
    """Combine 3-5 reference photos into ONE robust identity embedding.

    We embed each usable photo and average them (then re-normalize). Averaging
    multiple angles/lighting conditions yields a more stable centroid than any
    single shot.

    Raises
    ------
    EnrollmentError
        If fewer than `ENROLL_MIN_PHOTOS` usable faces are found.
    """
    n_in = len(images_bgr)
    if n_in < config.ENROLL_MIN_PHOTOS:
        raise EnrollmentError(
            f"Enrolment needs at least {config.ENROLL_MIN_PHOTOS} photos, got {n_in}."
        )

    # Respect the max — ignore extras beyond ENROLL_MAX_PHOTOS.
    usable_inputs = images_bgr[: config.ENROLL_MAX_PHOTOS]
    embeddings = embed_faces(usable_inputs, enforce_detection=True)

    if len(embeddings) < config.ENROLL_MIN_PHOTOS:
        raise EnrollmentError(
            f"Only {len(embeddings)} of {n_in} photos had a detectable face; "
            f"need at least {config.ENROLL_MIN_PHOTOS}."
        )

    centroid = np.mean(np.stack(embeddings, axis=0), axis=0)
    return _l2_normalize(centroid.astype(np.float32))


# ══════════════════════════════════════════════════════════════════════════
#  Similarity + matching
# ══════════════════════════════════════════════════════════════════════════

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity in [-1, 1]. Inputs need not be pre-normalized."""
    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0.0:
        return 0.0
    return float(np.dot(a, b) / denom)


def match_embedding(
    probe: np.ndarray,
    enrolled: Dict[int, np.ndarray],
    *,
    threshold: float | None = None,
) -> MatchResult:
    """Match a probe embedding against a dict of {student_id: embedding}.

    Returns the best match and whether it clears the cosine-similarity
    threshold (spec §5: ~0.5-0.6, default 0.55).
    """
    thr = config.RECOGNITION_COSINE_THRESHOLD if threshold is None else threshold

    best_id: Optional[int] = None
    best_sim: float = -1.0

    for student_id, ref in enrolled.items():
        sim = cosine_similarity(probe, ref)
        if sim > best_sim:
            best_sim = sim
            best_id = student_id

    if best_id is None:
        return MatchResult(matched_id=None, similarity=0.0, is_match=False)

    return MatchResult(
        matched_id=best_id,
        similarity=best_sim,
        is_match=best_sim >= thr,
    )


def identify_frame(
    image_bgr: np.ndarray,
    enrolled: Dict[int, np.ndarray],
    *,
    threshold: float | None = None,
) -> MatchResult:
    """Convenience: embed a frame then match it (tolerant of no-face frames).

    Uses `enforce_detection=False` so a transient no-face frame returns a
    non-match instead of raising — the scorer handles the "no face" semantics.
    """
    try:
        probe = embed_face(image_bgr, enforce_detection=False)
    except NoFaceDetected:
        return MatchResult(matched_id=None, similarity=0.0, is_match=False)
    return match_embedding(probe, enrolled, threshold=threshold)


# ══════════════════════════════════════════════════════════════════════════
#  Serialization helpers (embeddings ↔ JSON-friendly lists for DB storage)
# ══════════════════════════════════════════════════════════════════════════

def embedding_to_list(embedding: np.ndarray) -> List[float]:
    """Convert an embedding to a plain float list (for JSON/TEXT columns)."""
    return [float(x) for x in np.asarray(embedding).ravel()]


def embedding_from_list(values: List[float]) -> np.ndarray:
    """Rebuild an embedding array from a stored float list."""
    return np.asarray(values, dtype=np.float32)


# ══════════════════════════════════════════════════════════════════════════
#  Internals
# ══════════════════════════════════════════════════════════════════════════

def _l2_normalize(vec: np.ndarray) -> np.ndarray:
    """Scale a vector to unit L2 norm (no-op for a zero vector)."""
    norm = float(np.linalg.norm(vec))
    if norm == 0.0:
        return vec
    return (vec / norm).astype(np.float32)
