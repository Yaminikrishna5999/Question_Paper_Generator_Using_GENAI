"""
PDF Syllabus Extractor
Extracts text content and auto-detects topics from an uploaded PDF syllabus.
Requires: PyMuPDF (pip install PyMuPDF)
"""

import re
import io


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract all text from a PDF file's bytes. Returns plain text string."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text_parts = []
        for page in doc:
            text_parts.append(page.get_text())
        doc.close()
        return "\n".join(text_parts)
    except ImportError:
        raise ImportError("PyMuPDF is not installed. Run: pip install PyMuPDF")
    except Exception as e:
        raise RuntimeError(f"Failed to read PDF: {e}")

def extract_text_from_docx(docx_bytes: bytes) -> str:
    """Extract all text from a DOCX file's bytes."""
    try:
        from docx import Document
        doc = Document(io.BytesIO(docx_bytes))
        return "\n".join([para.text for para in doc.paragraphs])
    except ImportError:
        raise ImportError("python-docx is not installed. Run: pip install python-docx")
    except Exception as e:
        raise RuntimeError(f"Failed to read DOCX: {e}")

def extract_text_from_txt(txt_bytes: bytes) -> str:
    """Extract all text from a TXT file's bytes."""
    try:
        return txt_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return txt_bytes.decode("latin-1")
    except Exception as e:
        raise RuntimeError(f"Failed to read TXT: {e}")

def extract_text_auto(file_bytes, file_name):
    """Auto-detect file type and extract text."""
    ext = file_name.split(".")[-1].lower()
    if ext == "pdf":
        return extract_text_from_pdf(file_bytes)
    elif ext == "docx":
        return extract_text_from_docx(file_bytes)
    elif ext == "txt":
        return extract_text_from_txt(file_bytes)
    else:
        return ""


def extract_topics_from_pdf(pdf_bytes: bytes) -> list:
    """
    Extract candidate topics from a PDF.
    Returns a list of clean topic strings.
    """
    raw_text = extract_text_from_pdf(pdf_bytes)
    lines = raw_text.split("\n")

    topics = []
    seen = set()

    for line in lines:
        # Clean each line
        stripped = line.strip()

        # Skip empty lines, very short lines, or lines that are just numbers/symbols
        if len(stripped) < 4:
            continue
        if re.match(r'^[\d\s\.\-\*\•]+$', stripped):
            continue
        # Skip lines that are purely page numbers, headers etc.
        if re.match(r'^page\s*\d+$', stripped, re.IGNORECASE):
            continue

        # Clean up: remove leading bullets, numbers, special chars
        clean = re.sub(r'^[\d]+[\.\)]\s*', '', stripped)
        clean = re.sub(r'^[\-\*\•\–]\s*', '', clean)
        clean = clean.strip()

        # Keep lines that look like topic headings:
        # Not too long (headings < 120 chars), not pure sentences with lots of connectors
        if 5 <= len(clean) <= 120:
            # De-duplicate (case-insensitive)
            key = clean.lower()
            if key not in seen:
                seen.add(key)
                topics.append(clean)

    return topics


def summarize_pdf_text_for_prompt(pdf_bytes: bytes, max_chars: int = 4000) -> str:
    """
    Returns a truncated version of the PDF text suitable for injection into
    an AI prompt as syllabus context. Limits to max_chars to avoid token overflow.
    """
    raw_text = extract_text_from_pdf(pdf_bytes)
    # Collapse excessive whitespace
    cleaned = re.sub(r'\n{3,}', '\n\n', raw_text)
    cleaned = re.sub(r'[ \t]{2,}', ' ', cleaned)
    # Truncate
    if len(cleaned) > max_chars:
        cleaned = cleaned[:max_chars] + "\n...[Syllabus truncated for length]..."
    return cleaned.strip()
