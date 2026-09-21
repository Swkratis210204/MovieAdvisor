"""Optional: rewrite recommendation 'why' lines using a free, open-source LLM via Groq.

Groq hosts open-weight models (currently gpt-oss-20b) on a free-tier API, so this
needs no self-hosted infrastructure. Entirely optional — the app works fully
without it, using the deterministic why-text from recommender.py instead.

GROQ_API_KEY is a single secret shared across every visitor who enables this
feature (unlike TMDB, there's no "bring your own key" option for it), so a
hard daily call cap lives here too — it's the one thing in this app that can
actually cost money if usage spikes or the key leaks.
"""
from __future__ import annotations

import os
from datetime import date, timezone, datetime
from typing import Optional

import requests

from cache import DiskCache

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "openai/gpt-oss-20b"  # open-weight (Apache 2.0) model, hosted free-tier on Groq

# Hard cap on Groq calls per UTC day, shared across all visitors. Override with the
# GROQ_DAILY_CALL_LIMIT env var. Once hit, rewrite_why() silently falls back to the
# plain deterministic why-text instead of calling Groq again until the day rolls over.
DEFAULT_DAILY_LIMIT = int(os.environ.get("GROQ_DAILY_CALL_LIMIT", "300"))

_usage_cache = DiskCache(cache_dir=".cache/groq_usage")


def _usage_key(day: date) -> str:
    return f"groq_calls_{day.isoformat()}"


def get_daily_usage(today: Optional[date] = None) -> int:
    """How many Groq calls have been made today (UTC)."""
    today = today or datetime.now(timezone.utc).date()
    return _usage_cache.get(_usage_key(today)) or 0


def daily_limit_reached(limit: int = DEFAULT_DAILY_LIMIT, today: Optional[date] = None) -> bool:
    return get_daily_usage(today) >= limit


def _increment_daily_usage(today: Optional[date] = None) -> None:
    today = today or datetime.now(timezone.utc).date()
    key = _usage_key(today)
    _usage_cache.set(key, get_daily_usage(today) + 1)


def rewrite_why(
    why: str, title: str, profile_summary: str, api_key: str, daily_limit: int = DEFAULT_DAILY_LIMIT
) -> str:
    """Rewrite a 'why' line in more natural prose. Returns the original text on any failure
    or once the shared daily Groq call cap has been reached."""
    if not api_key:
        return why
    if daily_limit_reached(daily_limit):
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
        # Count the call against the daily cap as soon as it's sent — it already
        # cost against the Groq quota whether or not the response parses cleanly.
        _increment_daily_usage()
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except (requests.RequestException, KeyError, IndexError):
        return why
