#!/usr/bin/env python3
"""
Event Photo Finder
==================
Identifies photos of you inside an event gallery link,
using your own photos as face reference.

Usage:
    python main.py --url <gallery_url> --reference-dir <my_photos/>

See --help for all options.
"""

import argparse
import sys
from pathlib import Path

from face_matcher import find_my_photos, load_reference_encodings
from scraper import download_images, get_image_urls_html, get_image_urls_selenium


def _banner(text: str) -> None:
    width = 60
    print("\n" + "=" * width)
    print(f"  {text}")
    print("=" * width)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="event_photo_finder",
        description="Find your photos inside an event gallery.",
    )
    p.add_argument("--url", help="Event gallery URL (skip if using --skip-download)")
    p.add_argument(
        "--reference-dir",
        required=True,
        metavar="DIR",
        help="Folder with your reference photos (solo shots where your face is visible)",
    )
    p.add_argument(
        "--output-dir",
        default="my_event_photos",
        metavar="DIR",
        help="Where to save photos of you (default: my_event_photos/)",
    )
    p.add_argument(
        "--download-dir",
        default="event_photos_raw",
        metavar="DIR",
        help="Where to save downloaded event photos (default: event_photos_raw/)",
    )
    p.add_argument(
        "--tolerance",
        type=float,
        default=0.55,
        metavar="FLOAT",
        help=(
            "Face matching strictness, 0.0–1.0 (default: 0.55). "
            "Lower = fewer false positives; raise to 0.60–0.65 if missing matches."
        ),
    )
    p.add_argument(
        "--use-selenium",
        action="store_true",
        help=(
            "Use Selenium (headless Chrome) to scrape JavaScript-heavy sites "
            "like Pixieset, SmugMug, Shootproof. "
            "Requires Chrome + chromedriver installed."
        ),
    )
    p.add_argument(
        "--use-cnn",
        action="store_true",
        help=(
            "Use CNN face detection model (more accurate but much slower without GPU). "
            "Default is HOG (fast on CPU)."
        ),
    )
    p.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip the download step and use photos already in --download-dir.",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()

    if not args.skip_download and not args.url:
        print("Error: --url is required unless --skip-download is set.")
        sys.exit(1)

    ref_dir = Path(args.reference_dir)
    if not ref_dir.exists():
        print(f"Error: Reference directory '{ref_dir}' does not exist.")
        sys.exit(1)

    # ── Step 1: scrape image URLs ──────────────────────────────────────────
    if not args.skip_download:
        _banner(f"Step 1 – Fetching image URLs from gallery")
        print(f"  URL: {args.url}")

        if args.use_selenium:
            print("  Mode: Selenium (headless Chrome)")
            image_urls = get_image_urls_selenium(args.url)
        else:
            print("  Mode: HTML parser (fast)")
            image_urls = get_image_urls_html(args.url)

        print(f"  Found: {len(image_urls)} image URL(s)")

        if not image_urls:
            print(
                "\n  No images found via HTML parsing.\n"
                "  Tip: try adding --use-selenium for JavaScript-rendered galleries."
            )
            sys.exit(1)

        # ── Step 2: download ───────────────────────────────────────────────
        _banner(f"Step 2 – Downloading to '{args.download_dir}'")
        download_images(image_urls, args.download_dir)
    else:
        _banner("Steps 1–2 skipped (--skip-download)")

    # ── Step 3: load reference face encodings ──────────────────────────────
    _banner(f"Step 3 – Loading your reference photos from '{args.reference_dir}'")
    encodings = load_reference_encodings(ref_dir)

    if not encodings:
        print(
            "\n  No faces could be loaded from your reference photos.\n"
            "  Make sure the images clearly show your face and are not too small."
        )
        sys.exit(1)

    print(f"\n  {len(encodings)} face encoding(s) ready.")

    # ── Step 4: find matches ───────────────────────────────────────────────
    detection_model = "cnn" if args.use_cnn else "hog"
    _banner(
        f"Step 4 – Scanning event photos "
        f"(tolerance={args.tolerance}, model={detection_model})"
    )

    matches = find_my_photos(
        event_dir=args.download_dir,
        reference_encodings=encodings,
        output_dir=args.output_dir,
        tolerance=args.tolerance,
        detection_model=detection_model,
    )

    # ── Summary ────────────────────────────────────────────────────────────
    _banner("Done!")
    if matches:
        print(f"  Found {len(matches)} photo(s) with you in them.")
        print(f"  Saved to: {args.output_dir}/")
    else:
        print("  No matches found.")
        print(
            "  Tips:\n"
            "    • Increase --tolerance to 0.60 or 0.65\n"
            "    • Add more reference photos (different angles/lighting)\n"
            "    • Try --use-cnn for higher accuracy (slower)\n"
            "    • If the site uses JS, re-run with --use-selenium"
        )
    print()


if __name__ == "__main__":
    main()
