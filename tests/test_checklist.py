import pytest

from checklistpdf.__main__ import main
from checklistpdf.checklist import (ChecklistError, count_items, load_checklist,
                                    render_pdf, render_text, validate)

GOOD = {"title": "T", "sections": [{"name": "S", "items": ["a", "b"]}]}


def test_validate_good():
    assert validate(GOOD) is GOOD


@pytest.mark.parametrize("bad", [
    None, {}, {"title": "T"}, {"title": "T", "sections": []},
    {"title": "T", "sections": [{"items": ["a"]}]},
    {"title": "T", "sections": [{"name": "S", "items": []}]},
    {"title": "T", "sections": [{"name": "S", "items": ["a", " "]}]},
    {"title": "T", "sections": [{"name": "S", "items": [5]}]},
])
def test_validate_rejects(bad):
    with pytest.raises(ChecklistError):
        validate(bad)


def test_count_items():
    assert count_items(GOOD) == 2


def test_render_text_numbers_items():
    lines = render_text(GOOD)
    assert lines[0] == "T"
    assert "   [ ] Pass  [ ] Fail  1.2 b" in lines


def test_render_text_includes_location():
    data = dict(GOOD, location="Building A")
    assert "Location: Building A" in render_text(data)


def test_pdf_structure():
    pdf = render_pdf(["hello (world)"])
    assert pdf.startswith(b"%PDF-1.4") and pdf.rstrip().endswith(b"%%EOF")
    assert b"hello \\(world\\)" in pdf


def test_pdf_paginates():
    pdf = render_pdf([f"line {i}" for i in range(120)], lines_per_page=50)
    assert b"/Count 3" in pdf


def test_pdf_xref_offsets_point_at_objects():
    pdf = render_pdf(["x"])
    start = int(pdf.split(b"startxref\n")[1].split()[0])
    assert pdf[start:start + 4] == b"xref"


def test_load_invalid_yaml(tmp_path):
    p = tmp_path / "x.yaml"
    p.write_text("title: [unclosed")
    with pytest.raises(ChecklistError, match="invalid YAML"):
        load_checklist(p)


def test_cli_pdf(tmp_path, capsys):
    out = tmp_path / "o.pdf"
    assert main(["data/boiler-room.yaml", "--pdf", str(out)]) == 0
    assert out.read_bytes().startswith(b"%PDF")
    assert "8 items" in capsys.readouterr().out


def test_cli_missing_file(capsys):
    assert main(["nope.yaml"]) == 1
