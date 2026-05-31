import io
import shutil
import tempfile
import zipfile
from pathlib import Path

import face_recognition
import numpy as np
import streamlit as st
from PIL import Image

from face_matcher import _open_as_rgb, load_reference_encodings
from scraper import download_images, get_image_urls_html, get_image_urls_selenium

# ── Page config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Event Photo Finder",
    page_icon="📸",
    layout="wide",
)

st.title("📸 Event Photo Finder")
st.write("Encontre as fotos em que você aparece dentro de um álbum de evento.")

# ── Sidebar – reference photos & settings ─────────────────────────────────
with st.sidebar:
    st.header("Suas fotos de referência")
    st.caption("Envie fotos suas onde seu rosto esteja bem visível (sem óculos escuros).")
    reference_files = st.file_uploader(
        "Fotos de referência",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )
    if reference_files:
        st.success(f"{len(reference_files)} foto(s) carregada(s)")

    st.divider()
    st.header("Configurações")
    tolerance = st.slider(
        "Tolerância do reconhecimento",
        min_value=0.30,
        max_value=0.75,
        value=0.55,
        step=0.05,
        help=(
            "Menor = mais rigoroso (menos falsos positivos). "
            "Aumente se a ferramenta não estiver encontrando você."
        ),
    )

# ── Tabs: URL vs manual upload ─────────────────────────────────────────────
tab_url, tab_upload = st.tabs(
    ["🔗 Usar link do álbum (automático)", "📁 Enviar fotos do evento (manual)"]
)

with tab_url:
    url = st.text_input(
        "Cole o link do álbum",
        placeholder="https://fotografo.pic-time.com/client/...",
    )
    use_selenium = st.checkbox(
        "Usar navegador para carregar o site (recomendado para Pic-Time, Pixieset, SmugMug)",
        value=True,
        help="Requer Google Chrome instalado. Se não funcionar, use a aba de upload manual.",
    )
    run_url = st.button("Encontrar minhas fotos", type="primary", key="btn_url")

with tab_upload:
    st.caption(
        "Use esta opção quando o link automático não funcionar. "
        "Baixe as fotos do álbum pelo navegador e envie aqui."
    )
    event_files = st.file_uploader(
        "Fotos do evento",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        key="event_upload",
        label_visibility="collapsed",
    )
    if event_files:
        st.info(f"{len(event_files)} foto(s) do evento carregada(s)")
    run_upload = st.button("Encontrar minhas fotos", type="primary", key="btn_upload")


# ── Core processing logic ──────────────────────────────────────────────────
def _scan_photos(
    event_dir: Path,
    ref_dir: Path,
    tolerance: float,
) -> list[Path]:
    """Load reference encodings then scan event_dir for matches."""
    with st.spinner("Carregando suas fotos de referência..."):
        encodings = load_reference_encodings(ref_dir)

    if not encodings:
        st.error(
            "Não consegui detectar rostos nas suas fotos de referência. "
            "Use fotos com rosto bem visível, boa iluminação e sem óculos escuros."
        )
        return []

    st.success(f"{len(encodings)} rosto(s) de referência carregado(s).")

    _IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
    photos = sorted(p for p in event_dir.iterdir() if p.suffix.lower() in _IMAGE_EXTS)
    if not photos:
        st.error("Nenhuma foto encontrada na pasta do evento.")
        return []

    ref_array = np.array(encodings)
    matches: list[Path] = []
    output_dir = event_dir.parent / "matches"
    output_dir.mkdir(exist_ok=True)

    progress = st.progress(0.0, text="Analisando fotos do evento…")
    for i, photo in enumerate(photos):
        progress.progress((i + 1) / len(photos), text=f"Analisando {i+1} / {len(photos)}…")
        rgb = _open_as_rgb(photo)
        if rgb is None:
            continue
        locations = face_recognition.face_locations(rgb, model="hog")
        if not locations:
            continue
        for enc in face_recognition.face_encodings(rgb, locations):
            if float(face_recognition.face_distance(ref_array, enc).min()) <= tolerance:
                dest = output_dir / photo.name
                shutil.copy2(photo, dest)
                matches.append(dest)
                break

    progress.empty()
    return matches


def _show_results(matches: list[Path], tolerance: float) -> None:
    """Render matched photos and a zip download button."""
    if not matches:
        st.warning(
            "Nenhuma foto encontrada. Sugestões:\n"
            "- Aumente a tolerância na barra lateral (tente 0.60 ou 0.65)\n"
            "- Adicione mais fotos de referência com ângulos diferentes\n"
            "- Verifique se as fotos do evento têm boa resolução"
        )
        return

    st.success(f"🎉 {len(matches)} foto(s) encontrada(s) com você!")

    cols_per_row = 3
    for i in range(0, len(matches), cols_per_row):
        cols = st.columns(cols_per_row)
        for j, col in enumerate(cols):
            if i + j < len(matches):
                col.image(Image.open(matches[i + j]), use_container_width=True)

    # Build zip in memory
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for m in matches:
            zf.write(m, m.name)
    buf.seek(0)

    st.download_button(
        "⬇️ Baixar todas as fotos (.zip)",
        data=buf,
        file_name="minhas_fotos_evento.zip",
        mime="application/zip",
    )


# ── URL mode ───────────────────────────────────────────────────────────────
if run_url:
    if not reference_files:
        st.error("Envie pelo menos uma foto sua de referência na barra lateral.")
    elif not url or not url.strip():
        st.error("Informe o link do álbum.")
    else:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            ref_dir = tmpdir / "refs"
            ref_dir.mkdir()
            event_dir = tmpdir / "event"
            event_dir.mkdir()

            for f in reference_files:
                (ref_dir / f.name).write_bytes(f.read())

            with st.spinner("Buscando fotos no álbum…"):
                try:
                    image_urls = (
                        get_image_urls_selenium(url.strip())
                        if use_selenium
                        else get_image_urls_html(url.strip())
                    )
                except Exception as exc:
                    st.error(f"Erro ao acessar o link: {exc}")
                    image_urls = set()

            if not image_urls:
                st.warning(
                    "Não consegui baixar as fotos automaticamente.\n"
                    "Tente a aba **Enviar fotos do evento** para fazer upload manual."
                )
            else:
                st.info(f"{len(image_urls)} imagem(ns) encontrada(s) no álbum.")
                with st.spinner("Baixando fotos…"):
                    download_images(image_urls, event_dir)
                _show_results(_scan_photos(event_dir, ref_dir, tolerance), tolerance)

# ── Upload mode ────────────────────────────────────────────────────────────
if run_upload:
    if not reference_files:
        st.error("Envie pelo menos uma foto sua de referência na barra lateral.")
    elif not event_files:
        st.error("Envie as fotos do evento na aba acima.")
    else:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            ref_dir = tmpdir / "refs"
            ref_dir.mkdir()
            event_dir = tmpdir / "event"
            event_dir.mkdir()

            for f in reference_files:
                (ref_dir / f.name).write_bytes(f.read())
            for f in event_files:
                (event_dir / f.name).write_bytes(f.read())

            _show_results(_scan_photos(event_dir, ref_dir, tolerance), tolerance)
