import json
from types import SimpleNamespace

from llm_client import split_text_into_chunks


def test_split_text_respects_word_limit_and_prefers_paragraphs():
    raw_text = "one two\n\na b c d e"

    assert split_text_into_chunks(raw_text, max_words=3) == [
        "one two",
        "a b c",
        "d e",
    ]


def test_extraction_processes_chunks_and_combines_products(monkeypatch):
    import llm_client

    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.delenv("GROQ_MODEL", raising=False)
    monkeypatch.setattr(
        llm_client,
        "split_text_into_chunks",
        lambda _: ["milk list", "bread list"],
    )
    outputs = iter(
        [
            '{"products": [{"item_name": "Milk", "vendor_price": 50}]}',
            '[{"item_name": "Bread", "vendor_price": 40}]',
        ]
    )
    seen_chunks = []

    def fake_extract_chunk(chunk, model, api_key):
        seen_chunks.append((chunk, model, api_key))
        return next(outputs)

    monkeypatch.setattr(llm_client, "_extract_chunk", fake_extract_chunk)
    result = json.loads(llm_client.extract_catalog_from_text("milk list\n\nbread list"))

    assert [
        (product["item_name"], product["vendor_price"])
        for product in result["products"]
    ] == [("Milk", 50), ("Bread", 40)]
    assert len(seen_chunks) == 2
    assert all(call[1] == llm_client.DEFAULT_MODEL for call in seen_chunks)


def test_empty_model_responses_are_retried(monkeypatch):
    import llm_client
    from tenacity import wait_none

    call_count = 0

    class FakeCompletions:
        def create(self, **kwargs):
            nonlocal call_count
            assert kwargs["temperature"] == 0.0
            call_count += 1
            content = "" if call_count < 3 else "[]"
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
            )

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=FakeCompletions())
    )

    def fake_get_client(api_key):
        assert api_key == "test-key"
        return fake_client

    monkeypatch.setattr(llm_client, "_get_client", fake_get_client)
    extract_with_no_wait = llm_client._extract_chunk.retry_with(wait=wait_none())

    assert extract_with_no_wait("sample text", llm_client.DEFAULT_MODEL, "test-key") == "[]"
    assert call_count == 3


def test_select_fallback_model_uses_a_model_available_to_the_api_key():
    import llm_client

    available_ids = {"openai/gpt-oss-20b", "whisper-large-v3"}
    fake_client = SimpleNamespace(
        models=SimpleNamespace(
            list=lambda: SimpleNamespace(
                data=[SimpleNamespace(id=model_id) for model_id in available_ids]
            )
        )
    )

    assert llm_client._select_fallback_model(fake_client, set()) == "openai/gpt-oss-20b"
