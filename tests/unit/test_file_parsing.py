import io
import shutil
import zipfile
from pathlib import Path

import pytest

from app.utils.file_parsing import to_image_bytes

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

requires_soffice = pytest.mark.skipif(
    shutil.which("soffice") is None, reason="LibreOffice (soffice) not installed"
)


def _build_minimal_docx(text: str) -> bytes:
    """Hand-builds the minimal valid Office Open XML skeleton a .docx needs,
    without adding python-docx as a dependency just to generate test input."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>""",
        )
        z.writestr(
            "_rels/.rels",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>""",
        )
        z.writestr(
            "word/document.xml",
            f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body>
</w:document>""",
        )
    return buf.getvalue()


def test_to_image_bytes_pdf_returns_one_png_per_page():
    pdf_bytes = (FIXTURES_DIR / "sample_cv.pdf").read_bytes()

    pages = to_image_bytes(pdf_bytes, "application/pdf")

    assert len(pages) == 2
    for page in pages:
        assert page.startswith(PNG_MAGIC)


def test_to_image_bytes_image_passes_through_unchanged():
    fake_png = PNG_MAGIC + b"not a real image but has the right header"

    pages = to_image_bytes(fake_png, "image/png")

    assert pages == [fake_png]


def test_to_image_bytes_unsupported_mime_type_raises():
    with pytest.raises(ValueError, match="Unsupported CV file type"):
        to_image_bytes(b"whatever", "text/plain")


@requires_soffice
def test_to_image_bytes_docx_converts_via_libreoffice():
    docx_bytes = _build_minimal_docx("Sample CV DOCX")

    pages = to_image_bytes(
        docx_bytes,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )

    assert len(pages) >= 1
    assert pages[0].startswith(PNG_MAGIC)
