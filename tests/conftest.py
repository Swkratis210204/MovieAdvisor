import pytest

import llm_rewrite
from cache import DiskCache


@pytest.fixture(autouse=True)
def isolate_groq_usage_cache(tmp_path, monkeypatch):
    """Point the Groq daily-usage cap at a throwaway dir so running tests never
    inflates (or gets blocked by) the same on-disk counter the live app uses."""
    monkeypatch.setattr(llm_rewrite, "_usage_cache", DiskCache(cache_dir=tmp_path / "groq_usage"))
