import io
import subprocess
import tempfile
from pathlib import Path

from pdf2image import convert_from_bytes

_IMAGE_MIME_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp"}
_PDF_MIME_TYPE = "application/pdf"
_DOCX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

_SOFFICE_TIMEOUT_SECONDS = 60


def to_image_bytes(file_bytes: bytes, mime_type: str) -> list[bytes]:
    """Normalize an uploaded CV (PDF, DOCX, or image) into a list of PNG page
    images — one element per page, so a multimodal LLM call can read the CV
    visually without a separate OCR/text-extraction step."""
    if mime_type in _IMAGE_MIME_TYPES:
        return [file_bytes]

    if mime_type == _PDF_MIME_TYPE:
        return _pdf_to_png_pages(file_bytes)

    if mime_type == _DOCX_MIME_TYPE:
        pdf_bytes = _docx_to_pdf_bytes(file_bytes)
        return _pdf_to_png_pages(pdf_bytes)

    raise ValueError(f"Unsupported CV file type: {mime_type}")


def _pdf_to_png_pages(pdf_bytes: bytes) -> list[bytes]:
    pages = convert_from_bytes(pdf_bytes)
    png_pages = []
    for page in pages:
        buffer = io.BytesIO()
        page.save(buffer, format="PNG")
        png_pages.append(buffer.getvalue())
    return png_pages


def _docx_to_pdf_bytes(docx_bytes: bytes) -> bytes:
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        docx_path = tmp_path / "input.docx"
        docx_path.write_bytes(docx_bytes)

        subprocess.run(
            ["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(tmp_path), str(docx_path)],
            check=True,
            capture_output=True,
            timeout=_SOFFICE_TIMEOUT_SECONDS,
        )

        return (tmp_path / "input.pdf").read_bytes()
