import pytest

from app import config, llm
from app.schemas import Source

pytestmark = [pytest.mark.live, pytest.mark.skipif(not config.GROQ_API_KEY, reason="GROQ_API_KEY not set")]


def test_groq_streams_a_cited_answer_without_reasoning():
    """One real Groq call: streaming works, the answer cites its source, and no reasoning text leaks in."""
    sources = [Source(n=1, doc_id="00000000-0000-4000-8000-000000000001", doc_name="OS_Lecture3.pdf",
                      doc_type="pdf", location="p. 12",
                      text="A deadlock needs four conditions at once: mutual exclusion, hold and wait, "
                           "no preemption, and circular wait.")]

    model, pieces = llm.stream_answer("What conditions cause a deadlock?", sources)
    received = list(pieces)
    answer = "".join(received)

    assert model in config.LLM_MODELS
    assert len(received) > 1  # arrived as a stream, not one block
    assert "[1]" in answer and "circular wait" in answer.lower()
    assert "<think>" not in answer
