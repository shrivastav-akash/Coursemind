"""Builders for small test files, shared by several test modules."""

from fpdf import FPDF


def make_pdf(path, pages: list[str]):
    pdf = FPDF()
    pdf.set_font("Helvetica", size=11)
    for text in pages:
        pdf.add_page()
        if text:
            pdf.multi_cell(0, 6, text=text)
    pdf.output(str(path))
    return path
