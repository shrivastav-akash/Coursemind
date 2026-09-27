from fpdf import FPDF

from app.parsing import Section, chunk_sections, parse_pdf


def make_pdf(path, pages: list[str]):
    pdf = FPDF()
    pdf.set_font("Helvetica", size=11)
    for text in pages:
        pdf.add_page()
        if text:
            pdf.multi_cell(0, 6, text=text)
    pdf.output(str(path))
    return path


def test_pdf_one_section_per_page(tmp_path):
    path = make_pdf(tmp_path / "three.pdf", ["Deadlock basics.", "Paging and segmentation.", "Scheduling."])

    sections = parse_pdf(path)

    assert [(s.location, s.order) for s in sections] == [("p. 1", 1), ("p. 2", 2), ("p. 3", 3)]
    assert "Paging" in sections[1].text
    assert "\r" not in "".join(s.text for s in sections)


def test_long_page_splits_but_keeps_its_location(tmp_path):
    long_text = " ".join(f"Sentence {i} about mutual exclusion and hold and wait." for i in range(12))
    path = make_pdf(tmp_path / "long.pdf", ["Short intro.", long_text])

    chunks = chunk_sections(parse_pdf(path), size=120, overlap=20)

    page_two = [c for c in chunks if c.order == 2]
    assert len(page_two) > 1
    assert all(c.location == "p. 2" for c in page_two)
    assert all(len(c.text) <= 120 for c in chunks)
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))


def test_chunks_never_cross_sections():
    sections = [Section("p. 1", 1, "alpha " * 50), Section("p. 2", 2, "beta " * 50)]

    chunks = chunk_sections(sections, size=60, overlap=10)

    for c in chunks:
        assert ("alpha" in c.text) != ("beta" in c.text)
        assert c.location == ("p. 1" if "alpha" in c.text else "p. 2")


def test_pdf_without_text_gives_no_chunks(tmp_path):
    path = make_pdf(tmp_path / "blank.pdf", ["", ""])

    sections = parse_pdf(path)

    assert len(sections) == 2
    assert chunk_sections(sections, size=700, overlap=100) == []


def test_whitespace_only_sections_are_dropped():
    assert chunk_sections([Section("p. 1", 1, "  \n\n\t ")], size=700, overlap=100) == []
