from functools import lru_cache
from pathlib import Path
from typing import Any

SUPPORTED_IMAGE_TYPES = {".bmp", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp"}
MIN_NATIVE_TEXT_LENGTH = 80
MAX_OCR_IMAGE_DIMENSION = 1800
GOOD_OCR_SCORE = 16.0


@lru_cache(maxsize=1)
def _get_reader() -> Any:
    try:
        import easyocr
    except ImportError as error:
        raise RuntimeError(
            "Photo and scanned-PDF OCR requires EasyOCR. Install project "
            "dependencies with 'pip install -r requirements.txt'."
        ) from error

    try:
        return easyocr.Reader(["en", "hi"], gpu=False)
    except Exception as error:
        raise RuntimeError(
            "EasyOCR could not initialize. Check your internet connection so "
            "EasyOCR can download its English and Hindi recognition models."
        ) from error


def _prepare_image(image: Any) -> list[Any]:
    from PIL import Image, ImageEnhance, ImageFilter, ImageOps

    image = ImageOps.exif_transpose(image).convert("RGB")
    width, height = image.size
    scale = min(1.0, MAX_OCR_IMAGE_DIMENSION / max(width, height))
    if scale < 1:
        image = image.resize(
            (round(width * scale), round(height * scale)),
            Image.Resampling.LANCZOS,
        )

    grayscale = ImageOps.grayscale(image)
    enhanced = ImageOps.autocontrast(grayscale, cutoff=1)
    enhanced = ImageEnhance.Contrast(enhanced).enhance(1.5)
    enhanced = enhanced.filter(ImageFilter.SHARPEN)
    return [image, enhanced]


def _encode_image(image: Any) -> bytes:
    from io import BytesIO

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _read_image(image: Any) -> str:
    reader = _get_reader()
    best_text = ""
    best_score = 0.0

    for index, candidate in enumerate(_prepare_image(image)):
        options: dict[str, Any] = {
            "detail": 1,
            "paragraph": False,
            "min_size": 8,
            "contrast_ths": 0.1,
            "adjust_contrast": 0.7,
            "text_threshold": 0.55,
            "low_text": 0.25,
            "link_threshold": 0.35,
        }
        if index > 0:
            options["rotation_info"] = [90, 270]

        results = reader.readtext(
            _encode_image(candidate),
            **options,
        )
        lines = [
            (box, text.strip(), float(confidence))
            for box, text, confidence in results
            if text and text.strip()
        ]
        lines.sort(key=lambda result: (min(point[1] for point in result[0]), min(point[0] for point in result[0])))
        candidate_text = "\n".join(text for _, text, _ in lines)
        score = sum(len(text) * confidence for _, text, confidence in lines)
        if score > best_score:
            best_text = candidate_text
            best_score = score
        if best_score >= GOOD_OCR_SCORE:
            break

    return best_text


def _extract_image_text(image: Any) -> str:
    text = _read_image(image)
    if not text.strip():
        raise ValueError(
            "Could not read text from this photo. Try a sharper, brighter, "
            "straight-on photo with the full menu in frame."
        )
    return text


def extract_text_from_file(file_path: str) -> str:
    """Extract selectable PDF text and OCR from photos or scanned PDF pages."""
    suffix = Path(file_path).suffix.lower()
    if suffix in SUPPORTED_IMAGE_TYPES:
        from PIL import Image

        try:
            with Image.open(file_path) as image:
                return _extract_image_text(image)
        except (OSError, ValueError) as error:
            if isinstance(error, ValueError):
                raise
            raise ValueError(f"Could not open the uploaded image: {error}") from error

    if suffix != ".pdf":
        raise ValueError(f"Unsupported file format: {suffix or '[no extension]'}")

    try:
        import pdfplumber
    except ImportError as error:
        raise RuntimeError(
            "PDF text extraction requires pdfplumber. Install project "
            "dependencies with 'pip install -r requirements.txt'."
        ) from error

    page_texts: list[str] = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            native_text = page.extract_text() or ""
            if len(native_text.strip()) >= MIN_NATIVE_TEXT_LENGTH:
                page_texts.append(native_text.strip())
                continue

            page_image = page.to_image(resolution=300).original
            ocr_text = _extract_image_text(page_image)
            page_texts.append(ocr_text if len(ocr_text) > len(native_text.strip()) else native_text.strip())

    extracted_text = "\n\n".join(text for text in page_texts if text)
    if not extracted_text.strip():
        raise ValueError("No readable text was found in the uploaded PDF.")
    return extracted_text


def extract_text_from_pdf(file_path: str) -> str:
    """Backward-compatible alias for older PDF-only callers."""
    if Path(file_path).suffix.lower() != ".pdf":
        raise ValueError("Expected a PDF file")
    return extract_text_from_file(file_path)
