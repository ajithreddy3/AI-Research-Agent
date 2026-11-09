import re
from io import BytesIO

from pypdf import PdfReader


REFERENCE_HEADING_PATTERN = re.compile(
    r"^\s*(references|bibliography)\s*$",
    flags=re.IGNORECASE,
)


def extract_text_without_references(pdf_bytes: bytes) -> str:
    """
    Extract text page by page and stop once a references heading is found.
    This avoids indexing bibliography entries that can pollute retrieval quality.
    """
    reader = PdfReader(BytesIO(pdf_bytes))
    chunks: list[str] = []

    for page in reader.pages:
        page_text = page.extract_text() or ""
        lines = page_text.splitlines()

        cutoff_index = None
        for i, line in enumerate(lines):
            if REFERENCE_HEADING_PATTERN.match(line.strip()):
                cutoff_index = i
                break

        if cutoff_index is not None:
            valid_lines = lines[:cutoff_index]
            if valid_lines:
                chunks.append("\n".join(valid_lines))
            break

        chunks.append(page_text)

    return "\n".join(chunks).strip()
