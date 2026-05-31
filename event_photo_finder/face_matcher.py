import shutil
from pathlib import Path

import face_recognition
import numpy as np
from PIL import Image
from tqdm import tqdm

_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
_MIN_DIMENSION = 100  # skip images smaller than 100px on any side


def _open_as_rgb(path: Path) -> np.ndarray | None:
    """Load an image as an RGB numpy array, converting from RGBA/palette if needed."""
    try:
        img = Image.open(path)

        if min(img.size) < _MIN_DIMENSION:
            return None

        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        return np.array(img)
    except Exception:
        return None


def load_reference_encodings(reference_dir: str | Path) -> list[np.ndarray]:
    """
    Build face encodings from every image in *reference_dir*.
    Each image should clearly show your face.
    """
    reference_dir = Path(reference_dir)
    encodings: list[np.ndarray] = []

    photos = [p for p in reference_dir.iterdir() if p.suffix.lower() in _IMAGE_EXTS]
    if not photos:
        print(f"No images found in '{reference_dir}'.")
        return encodings

    print(f"Loading {len(photos)} reference photo(s)...")
    for photo in photos:
        rgb = _open_as_rgb(photo)
        if rgb is None:
            print(f"  Skipped (too small or unreadable): {photo.name}")
            continue

        faces = face_recognition.face_encodings(rgb)
        if not faces:
            print(f"  No face detected in: {photo.name}")
        elif len(faces) > 1:
            print(
                f"  {len(faces)} faces found in {photo.name} — "
                "using the first one. Prefer solo photos for best results."
            )
            encodings.append(faces[0])
        else:
            print(f"  Face loaded: {photo.name}")
            encodings.append(faces[0])

    return encodings


def find_my_photos(
    event_dir: str | Path,
    reference_encodings: list[np.ndarray],
    output_dir: str | Path,
    tolerance: float = 0.55,
    detection_model: str = "hog",
) -> list[Path]:
    """
    Scan every image in *event_dir* and copy matches to *output_dir*.

    Args:
        event_dir: Folder with downloaded event photos.
        reference_encodings: Face encodings from your reference photos.
        output_dir: Destination folder for photos where you appear.
        tolerance: Match threshold (0.0–1.0). Lower = stricter.
                   0.55 is a good default; lower if you see false positives.
        detection_model: "hog" (fast, CPU) or "cnn" (accurate, needs GPU/slow on CPU).
    """
    event_dir = Path(event_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not reference_encodings:
        raise ValueError("No reference encodings provided.")

    ref_array = np.array(reference_encodings)

    photos = sorted(p for p in event_dir.iterdir() if p.suffix.lower() in _IMAGE_EXTS)
    matches: list[Path] = []

    for photo in tqdm(photos, desc="Scanning event photos"):
        rgb = _open_as_rgb(photo)
        if rgb is None:
            continue

        locations = face_recognition.face_locations(rgb, model=detection_model)
        if not locations:
            continue

        encodings = face_recognition.face_encodings(rgb, locations)
        for enc in encodings:
            distances = face_recognition.face_distance(ref_array, enc)
            if float(distances.min()) <= tolerance:
                dest = output_dir / photo.name
                shutil.copy2(photo, dest)
                matches.append(dest)
                tqdm.write(f"  MATCH -> {photo.name}")
                break  # one match per photo is enough

    return matches
