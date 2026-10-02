import time

import groq
import httpx
import pytest
from langchain_core.messages import AIMessageChunk

from app import config, llm
from app.schemas import Source

SOURCES = [
    Source(n=1, doc_id="00000000-0000-4000-8000-000000000001", doc_name="DBMS.pptx", doc_type="pptx",
           location="slide 4", text="3NF removes transitive dependencies."),
    Source(n=2, doc_id="00000000-0000-4000-8000-000000000002", doc_name="OS_Lecture3.pdf", doc_type="pdf",
           location="p. 12", text="Deadlock needs four conditions."),
]


def rate_limit(per: str = "minute", remaining_requests: str = "900", retry_after: str | None = None):
    headers = {"x-ratelimit-remaining-requests": remaining_requests}
    if retry_after is not None:
        headers["retry-after"] = retry_after
    response = httpx.Response(429, headers=headers, request=httpx.Request("POST", "https://api.groq.com/x"))
    unit = "tokens per day (TPD)" if per == "day" else "tokens per minute (TPM)"
    return groq.RateLimitError(f"Rate limit reached for model `m` on {unit}: Limit 8000", response=response, body=None)


class FakeChat:
    """Stands in for ChatGroq: .stream() yields the given pieces, raising any exception instance in place."""

    def __init__(self, *events):
        self.events, self.calls = events, 0

    def stream(self, _messages):
        self.calls += 1
        for event in self.events:
            if isinstance(event, Exception):
                raise event
            yield AIMessageChunk(content=event)


@pytest.fixture
def models(monkeypatch):
    monkeypatch.setattr(config, "LLM_MODELS", ["m1", "m2"])
    monkeypatch.setattr(llm, "_exhausted_until", {})
    fakes: dict[str, FakeChat] = {}
    monkeypatch.setattr(llm, "_chat", lambda model: fakes[model])
    return fakes


def answer(question="What is 3NF?"):
    model, pieces = llm.stream_answer(question, SOURCES)
    return model, "".join(pieces)


def error_code(fn) -> str:
    with pytest.raises(llm.LLMError) as err:
        fn()
    return err.value.code


def test_prompt_numbers_sources_and_uses_the_exact_refusal():
    system, human = llm.build_prompt("What is 3NF?", SOURCES)

    assert system[0] == "system" and f"reply exactly: {config.REFUSAL}" in system[1]
    assert "answer that part and say which part your notes don't cover" in system[1]  # no all-or-nothing refusal
    # Without a worked [n] example and the number-only rule, gpt-oss-20b dropped markers in 12% of answers.
    assert "like this: 3NF removes transitive dependencies [2]." in system[1]
    assert "Refer to sources only by number, never by name" in system[1]
    assert human == ("human", "Sources:\n[1] (DBMS.pptx, slide 4)\n3NF removes transitive dependencies.\n\n"
                              "[2] (OS_Lecture3.pdf, p. 12)\nDeadlock needs four conditions.\n\nQuestion: What is 3NF?")


def test_first_model_answers(models):
    models.update(m1=FakeChat("", "3NF ", "removes [1]."), m2=FakeChat("unused"))

    assert answer() == ("m1", "3NF removes [1].")
    assert models["m2"].calls == 0


def test_minute_limit_falls_back_to_next_model(models):
    models.update(m1=FakeChat(rate_limit("minute")), m2=FakeChat("from m2"))

    assert answer() == ("m2", "from m2")
    assert llm._exhausted_until == {}  # a per-minute limit marks nothing


def test_daily_limit_on_every_model(models):
    models.update(m1=FakeChat(rate_limit(remaining_requests="0", retry_after="120")),
                  m2=FakeChat(rate_limit("day")))

    assert error_code(answer) == "daily_limit"
    now = time.time()
    assert 100 < llm._exhausted_until["m1"] - now <= 120  # retry-after header
    assert 590 < llm._exhausted_until["m2"] - now <= llm.DAILY_COOLDOWN_S  # no header: default


def test_minute_and_daily_mix_is_busy(models):
    models.update(m1=FakeChat(rate_limit("day")), m2=FakeChat(rate_limit("minute")))

    assert error_code(answer) == "llm_busy"
    assert list(llm._exhausted_until) == ["m1"]


def test_exhausted_model_is_skipped_until_its_time_passes(models):
    models.update(m1=FakeChat("from m1"), m2=FakeChat("from m2"))
    llm._exhausted_until["m1"] = time.time() + 60

    assert answer() == ("m2", "from m2")
    assert models["m1"].calls == 0

    llm._exhausted_until["m1"] = time.time() - 1
    assert answer() == ("m1", "from m1")


def test_all_models_exhausted_is_daily_limit_without_calls(models):
    models.update(m1=FakeChat("x"), m2=FakeChat("y"))
    llm._exhausted_until.update(m1=time.time() + 60, m2=time.time() + 60)

    assert error_code(answer) == "daily_limit"
    assert models["m1"].calls == models["m2"].calls == 0


def test_other_failure_before_first_token_is_llm_error_without_fallback(models):
    models.update(m1=FakeChat(RuntimeError("connection reset")), m2=FakeChat("unused"))

    assert error_code(answer) == "llm_error"
    assert models["m2"].calls == 0


def test_failure_after_first_token_keeps_partial_text(models):
    models.update(m1=FakeChat("Partial ", "answer", RuntimeError("stream cut")))
    model, pieces = llm.stream_answer("q?", SOURCES)
    received = []

    with pytest.raises(llm.LLMError) as err:
        for piece in pieces:
            received.append(piece)

    assert (model, received, err.value.code) == ("m1", ["Partial ", "answer"], "llm_error")
