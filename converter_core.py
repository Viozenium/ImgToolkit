"""Conversione delle immagini in JPG: nessuna dipendenza da tkinter."""

import os

from PIL import Image, ImageOps

# --------------------------------------------------------------------
# FORMATI SORGENTE ACCETTATI

FORMATS = [
    ("PNG", ".png"),
    ("JPEG", ".jpeg"),
    ("JPE", ".jpe"),
    ("BMP", ".bmp"),
    ("TIFF", ".tiff"),
    ("WEBP", ".webp"),
]

# --------------------------------------------------------------------
# LOGICA


def _unique_dest(destinazione, file_name):
    """Percorso di destinazione che non sovrascrive file esistenti."""
    dest = os.path.join(destinazione, f"{file_name}.jpg")
    n = 1
    while os.path.exists(dest):
        dest = os.path.join(destinazione, f"{file_name}_{n}.jpg")
        n += 1
    return dest


def _flatten_transparency(image):
    """Compone le aree trasparenti su sfondo bianco (invece che nero)."""
    if image.mode == "P":
        image = image.convert("RGBA")
    if image.mode in ("RGBA", "LA"):
        background = Image.new("RGB", image.size, (255, 255, 255))
        background.paste(image, mask=image.getchannel("A"))
        return background
    if image.mode != "RGB":
        return image.convert("RGB")
    return image


def _convert_to_jpg(destinazione, paths, quality, log=None, progress=None, fine=None):
    ok, failed = 0, 0
    total = len(paths)
    for i, file_path in enumerate(paths, start=1):
        try:
            with Image.open(file_path) as src:
                image = ImageOps.exif_transpose(src)
                exif = image.info.get("exif")
                icc = src.info.get("icc_profile")

            image = _flatten_transparency(image)

            file_name = os.path.splitext(os.path.basename(file_path))[0]
            jpg_file_path = _unique_dest(destinazione, file_name)

            save_kwargs = {"format": "JPEG", "quality": quality}
            if quality >= 95:
                save_kwargs["subsampling"] = 0
            if exif:
                save_kwargs["exif"] = exif
            if icc:
                save_kwargs["icc_profile"] = icc

            image.save(jpg_file_path, **save_kwargs)
            ok += 1
            if log:
                out_name = os.path.basename(jpg_file_path)
                suffix = f" → {out_name}" if out_name != f"{file_name}.jpg" else ""
                log(f"✅ {os.path.basename(file_path)}{suffix}")
        except Exception as e:
            failed += 1
            if log:
                log(f"❎ {os.path.basename(file_path)}: {e}")
        if progress:
            progress(i, total)
    if log:
        log(f"-- {ok} convertiti, {failed} falliti --")
    if fine:
        fine()
