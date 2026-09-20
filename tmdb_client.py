"""Thin TMDB API client with disk caching, rate limiting, and retries."""
from __future__ import annotations

import time
from typing import Any, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from cache import DiskCache

TMDB_BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w342"

# Minimum seconds between outgoing requests (basic client-side rate limiting)
MIN_REQUEST_INTERVAL = 0.05


class TMDBError(Exception):
    """Raised for TMDB auth/config errors that should stop the flow."""


class TMDBClient:
    def __init__(self, api_key: str, cache: Optional[DiskCache] = None):
        if not api_key:
            raise TMDBError("TMDB_API_KEY is missing. Add it to your .env file.")
        self.api_key = api_key
        self.cache = cache or DiskCache()
        self.session = self._build_session()
        self._last_request_time = 0.0

    @staticmethod
    def _build_session() -> requests.Session:
        session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < MIN_REQUEST_INTERVAL:
            time.sleep(MIN_REQUEST_INTERVAL - elapsed)
        self._last_request_time = time.monotonic()

    def _get(self, path: str, params: Optional[dict] = None, use_cache: bool = True) -> Any:
        params = dict(params or {})
        cache_key = f"{path}?{sorted(params.items())}"
        if use_cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached

        params["api_key"] = self.api_key
        self._throttle()
        try:
            resp = self.session.get(f"{TMDB_BASE_URL}{path}", params=params, timeout=15)
        except requests.RequestException as e:
            raise TMDBError(f"Network error calling TMDB: {e}") from e

        if resp.status_code == 401:
            raise TMDBError("TMDB API key is invalid (401 Unauthorized).")
        if resp.status_code == 404:
            return None
        try:
            resp.raise_for_status()
        except requests.HTTPError as e:
            raise TMDBError(f"TMDB API error: {e}") from e

        data = resp.json()
        if use_cache:
            self.cache.set(cache_key, data)
        return data

    def find_by_imdb_id(self, imdb_id: str) -> Optional[dict]:
        data = self._get(f"/find/{imdb_id}", params={"external_source": "imdb_id"})
        if not data:
            return None
        results = data.get("movie_results") or []
        return results[0] if results else None

    def get_recommendations(self, tmdb_id: int) -> list[dict]:
        data = self._get(f"/movie/{tmdb_id}/recommendations")
        return (data or {}).get("results", [])

    def get_similar(self, tmdb_id: int) -> list[dict]:
        data = self._get(f"/movie/{tmdb_id}/similar")
        return (data or {}).get("results", [])

    def get_external_ids(self, tmdb_id: int) -> dict:
        data = self._get(f"/movie/{tmdb_id}/external_ids")
        return data or {}

    def get_movie_details(self, tmdb_id: int) -> Optional[dict]:
        return self._get(f"/movie/{tmdb_id}")

    def get_credits(self, tmdb_id: int) -> dict:
        data = self._get(f"/movie/{tmdb_id}/credits")
        return data or {}

    def get_movie_full(self, tmdb_id: int) -> Optional[dict]:
        """Fetch movie details + external_ids + credits in a single request."""
        return self._get(
            f"/movie/{tmdb_id}",
            params={"append_to_response": "external_ids,credits"},
        )

    def get_genre_map(self) -> dict[int, str]:
        data = self._get("/genre/movie/list")
        genres = (data or {}).get("genres", [])
        return {g["id"]: g["name"] for g in genres}

    @staticmethod
    def poster_url(poster_path: Optional[str]) -> Optional[str]:
        if not poster_path:
            return None
        return f"{IMAGE_BASE_URL}{poster_path}"
