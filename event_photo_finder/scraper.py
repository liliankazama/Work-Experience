import re
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}
_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
_MIN_IMAGE_SIZE_BYTES = 20_000  # skip thumbnails smaller than ~20 KB


def _is_image_url(url: str) -> bool:
    path = url.lower().split("?")[0]
    return any(path.endswith(ext) for ext in _IMAGE_EXTS)


def _make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(_HEADERS)
    return session


def get_image_urls_html(url: str, session: requests.Session | None = None) -> set[str]:
    """Extract full-resolution image URLs from a plain HTML gallery page."""
    if session is None:
        session = _make_session()

    resp = session.get(url, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    found: set[str] = set()

    # <img src / data-src / data-lazy-src / data-original>
    for img in soup.find_all("img"):
        for attr in ("src", "data-src", "data-lazy-src", "data-original", "data-full"):
            src = img.get(attr)
            if src:
                found.add(urljoin(url, src))

    # <a href="...jpg"> (linked full-res images)
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if _is_image_url(href):
            found.add(urljoin(url, href))

    # CSS background-image: url(...)
    for elem in soup.find_all(style=True):
        for match in re.findall(r'url\(["\']?(.*?)["\']?\)', elem["style"]):
            if match:
                found.add(urljoin(url, match))

    return {u for u in found if _is_image_url(u)}


def get_image_urls_selenium(url: str) -> set[str]:
    """
    Fallback scraper using Selenium for JavaScript-heavy gallery sites
    (Pixieset, SmugMug, Shootproof, etc.).

    Requires: Google Chrome + chromedriver installed, and `selenium` package.
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
    except ImportError:
        raise RuntimeError(
            "selenium is not installed. Run: pip install selenium"
        )

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=options)
    found: set[str] = set()

    try:
        driver.get(url)
        # Scroll to trigger lazy loading
        last_height = 0
        for _ in range(20):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.5)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        soup = BeautifulSoup(driver.page_source, "html.parser")
        for img in soup.find_all("img"):
            for attr in ("src", "data-src", "data-lazy-src", "data-original", "data-full"):
                src = img.get(attr)
                if src:
                    found.add(urljoin(url, src))

        for a in soup.find_all("a", href=True):
            if _is_image_url(a["href"]):
                found.add(urljoin(url, a["href"]))
    finally:
        driver.quit()

    return {u for u in found if _is_image_url(u)}


def download_images(
    urls: set[str],
    output_dir: str | Path,
    session: requests.Session | None = None,
    skip_small: bool = True,
) -> list[Path]:
    """Download images to *output_dir*, skipping already-downloaded files."""
    if session is None:
        session = _make_session()

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    downloaded: list[Path] = []
    url_list = sorted(urls)

    for i, url in enumerate(tqdm(url_list, desc="Downloading"), 1):
        ext = Path(url.split("?")[0]).suffix.lower() or ".jpg"
        filename = f"photo_{i:04d}{ext}"
        filepath = output_dir / filename

        if filepath.exists():
            downloaded.append(filepath)
            continue

        try:
            resp = session.get(url, timeout=30, stream=True)
            if resp.status_code != 200:
                continue

            content = resp.content
            if skip_small and len(content) < _MIN_IMAGE_SIZE_BYTES:
                continue  # likely a thumbnail

            filepath.write_bytes(content)
            downloaded.append(filepath)
        except Exception as exc:
            tqdm.write(f"  Skipped {url}: {exc}")

    return downloaded
