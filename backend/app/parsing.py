from dataclasses import dataclass
from pathlib import Path

import pypdfium2 as pdfium
from langchain_text_splitters import RecursiveCharacterTextSplitter


@dataclass(frozen=True)
class Section:
    location: str  # display label: "p. 12", "slide 4", "§ Normal forms"
    order: int     # page / slide / section number, 1-based
    text: str


@dataclass(frozen=True)
class Chunk:
    location: str
    order: int
    chunk_index: int  # 0-based position within the document
    text: str


def parse_pdf(path: Path | str) -> list[Section]:
    pdf = pdfium.PdfDocument(path)
    try:
        sections = []
        for i in range(len(pdf)):
            page = pdf[i]
            textpage = page.get_textpage()
            text = textpage.get_text_range().replace("\r\n", "\n")
            # Close per page: a 500-page PDF would otherwise hold every page in memory on a 512 MB host.
            textpage.close()
            page.close()
            sections.append(Section(f"p. {i + 1}", i + 1, text))
        return sections
    finally:
        pdf.close()


def chunk_sections(sections: list[Section], size: int, overlap: int) -> list[Chunk]:
    # Each section is split on its own so a chunk never spans two pages/slides/sections.
    splitter = RecursiveCharacterTextSplitter(chunk_size=size, chunk_overlap=overlap)
    chunks: list[Chunk] = []
    for section in sections:
        for piece in splitter.split_text(section.text):
            if piece.strip():
                chunks.append(Chunk(section.location, section.order, len(chunks), piece))
    return chunks
