"""Optional: rewrite recommendation 'why' lines using a free, open-source LLM via Groq.

Groq hosts open-weight models (currently gpt-oss-20b) on a free-tier API, so this
needs no self-hosted infrastructure. Entirely optional — the app works fully
without it, using the deterministic why-text from recommender.py instead.
"""
from __future__ import annotations

import requests

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "openai/gpt-oss-20b"  # open-weight (Apache 2.0) model, hosted free-tier on Groq


def rewrite_why(why: str, title: str, profile_summary: str, api_key: str) -> str:
    """Rewrite a 'why' line in more natural prose. Returns the original text on any failure."""
    if not api_key:
        return why

    prompt = (
        f"Rewrite this movie recommendation reason for '{title}' as one natural, friendly "
        f"sentence (max 25 words). Keep it strictly factual — do not invent details not "
        f"present in the reason data, and do not list '{title}' itself as one of the "
        f"viewer's favorites (it is the movie being recommended, not a source).\n\n"
        f"Viewer profile: {profile_summary}\n"
        f"Reason data: {why}"
    )

    try:
        resp = requests.post(
            GROQ_API_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": GROQ_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 300,
                "temperature": 0.6,
                "reasoning_effort": "low",
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except (requests.RequestException, KeyError, IndexError):
        return why
