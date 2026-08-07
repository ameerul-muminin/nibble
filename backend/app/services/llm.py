"""Ask the language model a question, using only the retrieved notes.

The system prompt does double duty: it enforces grounding (answer from the
notes, admit when they do not cover it) and it gives Nibble its voice.
"""

import httpx

from app.core.config import get_settings

_OPENAI_URL = "https://api.openai.com/v1/chat/completions"

SYSTEM_PROMPT = """You are Nibble, a cheerful cat who helps students study.

Rules you never break:
- Answer ONLY from the notes provided below. They are the student's own material.
- If the notes do not cover the question, say so plainly and suggest what to
  upload. Never invent facts to fill a gap.
- Cite the page you used, like "(p. 4)".

Voice: warm, short sentences, plain words. Explain like a friend who already
did the reading. One small cat-ish flourish is fine; do not overdo it."""


def build_context(snippets: list[tuple[str, str, int]]) -> str:
    """snippets: (filename, content, page)"""
    return "\n\n".join(
        f"[{filename} - p.{page}]\n{content}" for filename, content, page in snippets
    )


async def answer_question(question: str, context: str) -> str:
    settings = get_settings()
    if not settings.llm_api_key:
        raise RuntimeError("LLM_API_KEY is not set. Copy .env.example to .env and fill it in.")

    user_content = f"Notes:\n{context}\n\nQuestion: {question}"

    async with httpx.AsyncClient(timeout=90) as client:
        response = await client.post(
            _OPENAI_URL,
            headers={"Authorization": f"Bearer {settings.llm_api_key}"},
            json={
                "model": settings.llm_chat_model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                "temperature": 0.3,
            },
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
