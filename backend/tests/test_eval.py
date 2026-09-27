from eval.run_eval import both, first_rank, hit

GUIDE = "guide.docx"
PDF = "notes.pdf"


def test_a_hit_needs_the_location_and_one_of_the_phrases():
    q = {"expect": [{"doc": GUIDE, "location": "§ 11"}], "has": [".env"]}
    same_section_other_chunk = (GUIDE, "§ 11", "Ignore Vim swap files\n*.swp")
    answer_chunk = (GUIDE, "§ 11", "# Ignore secrets\n.ENV\n*.local")

    assert not hit(q, [same_section_other_chunk])
    assert hit(q, [answer_chunk])  # case and line breaks don't matter
    assert first_rank(q, [same_section_other_chunk, answer_chunk]) == 2


def test_location_alone_is_enough_without_phrases():
    q = {"expect": [{"doc": GUIDE, "location": "§ 6.2"}]}
    assert hit(q, [(GUIDE, "§ 6.2", "anything")])
    assert not hit(q, [(PDF, "§ 6.2", "anything")])


def test_two_document_question_needs_every_part():
    q = {"parts": [
        {"expect": [{"doc": PDF, "location": "p. 2"}], "has": ["sub directories"]},
        {"expect": [{"doc": GUIDE, "location": "§ 11"}], "has": [".env"]},
    ]}
    pdf_part = (PDF, "p. 2", "ignoring will\nwork for the current and sub\ndirectories")
    guide_part = (GUIDE, "§ 11", ".env")

    assert hit(q, [pdf_part]) and not both(q, [pdf_part])
    assert both(q, [guide_part, pdf_part])
