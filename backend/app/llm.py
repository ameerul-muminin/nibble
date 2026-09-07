"""Talk to the language model (Groq / Llama) and get an answer from notes.

Alif owns this file. It is the only place in the backend that knows how to
call a language model. Everything else — the prompt, the API key, the
network call — lives here so there is exactly one file to debug when the
model does something unexpected.

The function you care about is ``ask_with_sources``. It takes a question and
a list of context chunks (the output of ``search_chunks`` from
``embeddings.py``), builds a prompt, calls Groq, and returns the answer with
the sources that were used.
"""

import requests

from app import config

# ---------------------------------------------------------------------------
# System prompt — the instructions the model always sees
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are Nibble, a helpful study assistant. You answer questions using ONLY
the lecture notes provided below. Follow these rules strictly:

1. Answer ONLY from the notes. If the notes do not contain enough information
   to answer, say: "I don't have enough information in your notes to answer
   that."
2. Be concise and clear. Use simple language a student would understand.
3. When you use information from a specific page, mention it naturally in your
   answer like "(p. 4)" or "(p. 12)".
4. Never make up facts, statistics, or details that are not in the notes.
5. Never say "according to the notes" — just answer directly.
"""


def _build_context_block(chunks: list[dict]) -> str:
    """Turn a list of search-result chunks into a text block for the prompt.

    Each chunk dict is expected to have at least ``page``, ``content``, and
    ``filename``.
    """
    if not chunks:
        return "(No relevant notes found.)"

    parts: list[str] = []
    for chunk in chunks:
        filename = chunk.get("filename", "unknown")
        page = chunk.get("page", "?")
        content = chunk.get("content", "")
        parts.append(f"--- {filename}, page {page} ---\n{content}")

    return "\n\n".join(parts)


def _build_messages(question: str, chunks: list[dict]) -> list[dict]:
    """Build the list of messages to send to the chat model."""
    context = _build_context_block(chunks)

    user_message = f"Here are the relevant notes:\n\n{context}\n\nQuestion: {question}"

    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]


def _extract_sources(chunks: list[dict]) -> list[dict]:
    """Build the ``sources`` array for the response from the search results."""
    return [
        {
            "document_id": chunk.get("document_id"),
            "filename": chunk.get("filename", "unknown"),
            "page": chunk.get("page"),
            "excerpt": chunk.get("content", "")[:200],
        }
        for chunk in chunks
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def ask_with_sources(question: str, context_chunks: list[dict]) -> dict:
    """Send a question to the LLM with context chunks and return an answer.

    Parameters:
        question: The student's question, e.g. "explain osmosis simply".
        context_chunks: A list of chunk dicts from ``search_chunks``. Each
            dict should contain ``document_id``, ``filename``, ``page``,
            ``content``, and ``score``.

    Returns:
        A dict with two keys:
        - ``answer``: the model's response string.
        - ``sources``: a list of source dicts (document_id, filename, page,
          excerpt) that were used as context.

    Raises:
        RuntimeError: If the API key is missing or the Groq call fails.
    """
    if not config.GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Get a free key at "
            "https://console.groq.com/keys and add it to backend/.env"
        )

    messages = _build_messages(question, context_chunks)

    # --- Call the Groq API (OpenAI-compatible) ----------------------------
    headers = {
        "Authorization": f"Bearer {config.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": config.CHAT_MODEL,
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 1024,
    }

    try:
        resp = requests.post(
            f"{config.GROQ_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"Groq API call failed: {exc}") from exc

    data = resp.json()
    answer = data["choices"][0]["message"]["content"].strip()

    return {
        "answer": answer,
        "sources": _extract_sources(context_chunks),
    }
