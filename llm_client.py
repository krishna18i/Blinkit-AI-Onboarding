import json
import logging
import os
from functools import lru_cache

from dotenv import find_dotenv, load_dotenv
from groq import (
    APIConnectionError,
    APITimeoutError,
    Groq,
    NotFoundError,
    RateLimitError,
)
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from parser import parse_and_validate_json

load_dotenv(find_dotenv())

DEFAULT_MODEL = "llama-3.1-8b-instant"
FALLBACK_MODELS = (
    "llama-3.3-70b-versatile",
    "openai/gpt-oss-20b",
    "qwen/qwen3-32b",
    "meta-llama/llama-4-scout-17b-16e-instruct",
)
MAX_CHUNK_WORDS = 500
MAX_COMPLETION_TOKENS = 8192
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are an Enterprise Catalog Data Extraction AI.
Extract every product in the supplied vendor text and return only JSON.
Return either an object with a "products" array or a raw array of products.
Each product must have item_name, vendor_price, category, and seo_description.
Extract vendor_price as the single price explicitly printed by the vendor,
whether it is listed as a price, rate, or MRP. Return it as a number without
currency symbols. Never estimate, calculate, split, or relabel prices as
company cost or selling prices. If no price is legible, omit that product.
Use a concise category and a useful two-sentence SEO description.
Do not include commentary or fields other than those product fields.
"""


class EmptyLLMResponseError(RuntimeError):
    """Raised when the model returns no usable response text."""


def split_text_into_chunks(raw_text: str, max_words: int = MAX_CHUNK_WORDS) -> list[str]:
    """Split text on paragraph boundaries where possible, capped by word count."""
    if max_words < 1:
        raise ValueError("max_words must be at least 1")

    paragraphs = [paragraph.strip() for paragraph in raw_text.split("\n\n") if paragraph.strip()]
    chunks: list[str] = []
    current_parts: list[str] = []
    current_word_count = 0

    for paragraph in paragraphs:
        words = paragraph.split()
        pieces = [
            " ".join(words[index : index + max_words])
            for index in range(0, len(words), max_words)
        ]

        for piece in pieces:
            piece_word_count = len(piece.split())
            if current_parts and current_word_count + piece_word_count > max_words:
                chunks.append("\n\n".join(current_parts))
                current_parts = []
                current_word_count = 0

            current_parts.append(piece)
            current_word_count += piece_word_count

    if current_parts:
        chunks.append("\n\n".join(current_parts))

    return chunks


@lru_cache(maxsize=1)
def _get_client(api_key: str) -> Groq:
    return Groq(api_key=api_key, max_retries=0)


def _select_fallback_model(client: Groq, unavailable_models: set[str]) -> str:
    available_models = {model.id for model in client.models.list().data}
    for candidate in FALLBACK_MODELS:
        if candidate in available_models and candidate not in unavailable_models:
            return candidate

    available_candidates = ", ".join(
        model_id
        for model_id in sorted(available_models)
        if model_id not in unavailable_models
    )
    raise RuntimeError(
        "Groq rejected the configured model and no supported fallback model is "
        "available to this API key. Set GROQ_MODEL to a chat model available in "
        f"your Groq account. Available model IDs: {available_candidates or 'none'}"
    )


@retry(
    retry=retry_if_exception_type(
        (
            APIConnectionError,
            APITimeoutError,
            RateLimitError,
            ConnectionError,
            TimeoutError,
            EmptyLLMResponseError,
        )
    ),
    wait=wait_fixed(2),
    stop=stop_after_attempt(3),
    reraise=True,
)
def _extract_chunk(chunk: str, model: str, api_key: str) -> str:
    response = _get_client(api_key).chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Extract products from this vendor text:\n{chunk}"},
        ],
        temperature=0.0,
        max_tokens=MAX_COMPLETION_TOKENS,
    )
    if not response.choices:
        raise EmptyLLMResponseError("Groq returned no completion choices")

    content = response.choices[0].message.content
    if not content or not content.strip():
        raise EmptyLLMResponseError("Groq returned an empty response")
    return content


def extract_catalog_from_text(raw_text: str, model: str | None = None) -> str:
    """Extract and combine products from independently processed text chunks."""
    chunks = split_text_into_chunks(raw_text)
    if not chunks:
        raise ValueError("Vendor text is empty; there is nothing to extract")

    raw_key = os.getenv("GROQ_API_KEY")
    if not raw_key or not raw_key.strip():
        raise ValueError("GROQ_API_KEY not found in .env or environment")

    selected_model = model or os.getenv("GROQ_MODEL", DEFAULT_MODEL)
    products = []
    for chunk in chunks:
        tried_models: set[str] = set()
        chunk_model = selected_model
        while True:
            try:
                chunk_output = _extract_chunk(chunk, chunk_model, raw_key.strip())
                break
            except NotFoundError:
                tried_models.add(chunk_model)
                fallback_model = _select_fallback_model(
                    _get_client(raw_key.strip()),
                    tried_models,
                )
                logger.warning(
                    "Groq model %s was unavailable; retrying chunk with %s",
                    chunk_model,
                    fallback_model,
                )
                chunk_model = fallback_model

        selected_model = chunk_model
        products.extend(parse_and_validate_json(chunk_output)["products"])

    return json.dumps({"products": products}, ensure_ascii=False)
