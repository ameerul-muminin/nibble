"""Turn text into vectors.

An embedding is a long list of numbers that stands for the MEANING of a piece
of text. Two chunks about the same topic get similar numbers. That is the
whole trick behind "find the notes relevant to this question".

Everything provider-specific is behind embed_texts(), so swapping providers
later touches exactly one function.
"""

import httpx

from app.core.config import get_settings

_OPENAI_URL = "https://api.openai.com/v1/embeddings"


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of strings. Batch, don't loop — it is far cheaper."""
    if not texts:
        return []

    settings = get_settings()
    if not settings.llm_api_key:
        raise RuntimeError("LLM_API_KEY is not set. Copy .env.example to .env and fill it in.")

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            _OPENAI_URL,
            headers={"Authorization": f"Bearer {settings.llm_api_key}"},
            json={"model": settings.llm_embedding_model, "input": texts},
        )
        response.raise_for_status()
        payload = response.json()

    ordered = sorted(payload["data"], key=lambda item: item["index"])
    return [item["embedding"] for item in ordered]


async def embed_query(text: str) -> list[float]:
    return (await embed_texts([text]))[0]
