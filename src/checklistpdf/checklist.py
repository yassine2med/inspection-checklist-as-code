"""Load a YAML inspection checklist and render it as text or a simple PDF."""
from __future__ import annotations

from pathlib import Path

import yaml


class ChecklistError(ValueError):
    """Raised when a checklist file is missing fields or malformed."""


def load_checklist(path: str | Path) -> dict:
    """Read and validate a checklist file. Returns the parsed dict."""
    with open(path, encoding="utf-8") as handle:
        try:
            data = yaml.safe_load(handle)
        except yaml.YAMLError as exc:
            raise ChecklistError(f"invalid YAML: {exc}") from exc
    return validate(data)


def validate(data: object) -> dict:
    """Check structure: title, and sections each with a name and non-empty items."""
    if not isinstance(data, dict) or not data.get("title"):
        raise ChecklistError("checklist needs a title")
    sections = data.get("sections")
    if not isinstance(sections, list) or not sections:
        raise ChecklistError("checklist needs at least one section")
    for number, section in enumerate(sections, start=1):
        if not isinstance(section, dict) or not section.get("name"):
            raise ChecklistError(f"section {number} needs a name")
        items = section.get("items")
        if not isinstance(items, list) or not items:
            raise ChecklistError(f"section '{section['name']}' needs items")
        if any(not isinstance(i, str) or not i.strip() for i in items):
            raise ChecklistError(f"section '{section['name']}' has an empty item")
    return data


def count_items(data: dict) -> int:
    """Total number of check items."""
    return sum(len(s["items"]) for s in data["sections"])


def render_text(data: dict) -> list[str]:
    """Return the printable lines of the checklist, with a pass/fail box per item."""
    lines = [data["title"].upper()]
    if data.get("location"):
        lines.append(f"Location: {data['location']}")
    lines += ["Inspector: ____________________   Date: ______________", ""]
    for number, section in enumerate(data["sections"], start=1):
        lines.append(f"{number}. {section['name']}")
        for index, item in enumerate(section["items"], start=1):
            lines.append(f"   [ ] Pass  [ ] Fail  {number}.{index} {item}")
        lines.append("")
    lines.append("Notes:")
    return lines


def _escape(text: str) -> str:
    text = text.encode("latin-1", "replace").decode("latin-1")
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def render_pdf(lines: list[str], lines_per_page: int = 50) -> bytes:
    """Build a minimal multi-page PDF (Helvetica 10 pt) from text lines."""
    pages = [lines[i:i + lines_per_page] for i in range(0, len(lines), lines_per_page)] or [[]]
    objects: list[bytes] = []
    first_page_id = 4
    kids = " ".join(f"{first_page_id + 2 * n} 0 R" for n in range(len(pages)))
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode())
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    for n, page in enumerate(pages):
        content_id = first_page_id + 2 * n + 1
        objects.append((f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                        f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>").encode())
        body = ["BT", "/F1 10 Tf", "13 TL", "50 750 Td"]
        body += [f"({_escape(line)}) Tj T*" for line in page]
        body.append("ET")
        stream = "\n".join(body).encode("latin-1")
        objects.append(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream")
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)
