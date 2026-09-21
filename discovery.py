"""Discovery / explore mode: trending, genre-gap, and opposite-of-you picks.

Unlike recommender.py, these don't need the seed/fan-out scoring machinery —
each lens is a single direct TMDB call (trending or discover-by-genre).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd

from taste_profile import TasteProfile
from tmdb_client import TMDBClient

DISCOVER_MIN_VOTES = 200
POOL_SIZE = 10


@dataclass
class DiscoveryCard:
    tmdb_id: int
    title: str
    year: Optional[int]
    genres: list[str]
    vote_average: float
    vote_count: int
    poster_path: Optional[str]
    why: str

    @property
    def tmdb_url(self) -> str:
        return f"https://www.themoviedb.org/movie/{self.tmdb_id}"


def _already_rated_keys(df: pd.DataFrame) -> set[tuple[str, Optional[int]]]:
    """(lowercase title, year) pairs for movies the user has already rated."""
    keys = set()
    for _, row in df.iterrows():
        year = int(row["year"]) if pd.notna(row["year"]) else None
        keys.add((str(row["title"]).strip().lower(), year))
    return keys


def _movie_to_card(m: dict, genre_map: dict[int, str], why: str) -> DiscoveryCard:
    genres = [genre_map[g] for g in m.get("genre_ids", []) if g in genre_map]
    release_date = m.get("release_date") or ""
    year = int(release_date[:4]) if release_date[:4].isdigit() else None
    return DiscoveryCard(
        tmdb_id=m["id"],
        title=m.get("title", ""),
        year=year,
        genres=genres,
        vote_average=float(m.get("vote_average") or 0.0),
        vote_count=int(m.get("vote_count") or 0),
        poster_path=m.get("poster_path"),
        why=why,
    )


def _filter_and_build(
    results: list[dict],
    genre_map: dict[int, str],
    rated_keys: set[tuple[str, Optional[int]]],
    why: str,
    seen_ids: set[int],
    limit: int,
) -> list[DiscoveryCard]:
    cards = []
    for m in results:
        if len(cards) >= limit:
            break
        tmdb_id = m.get("id")
        if tmdb_id is None or tmdb_id in seen_ids:
            continue
        release_date = m.get("release_date") or ""
        year = int(release_date[:4]) if release_date[:4].isdigit() else None
        title = m.get("title", "")
        if (title.strip().lower(), year) in rated_keys:
            continue
        seen_ids.add(tmdb_id)
        cards.append(_movie_to_card(m, genre_map, why))
    return cards


def get_trending_picks(df: pd.DataFrame, client: TMDBClient, limit: int = POOL_SIZE) -> list[DiscoveryCard]:
    """Movies trending this week, excluding anything already rated."""
    genre_map = client.get_genre_map()
    rated_keys = _already_rated_keys(df)
    results = client.get_trending()
    return _filter_and_build(results, genre_map, rated_keys, "Trending this week on TMDB", set(), limit)


def get_genre_gap_picks(
    df: pd.DataFrame, profile: TasteProfile, client: TMDBClient, limit: int = POOL_SIZE
) -> list[DiscoveryCard]:
    """Well-regarded movies in genres you rarely rate."""
    genre_map = client.get_genre_map()
    name_to_id = {name: gid for gid, name in genre_map.items()}
    rated_counts = {name: a.count for name, a in profile.genre_affinities.items()}
    gap_genres = sorted(genre_map.values(), key=lambda name: rated_counts.get(name, 0))

    rated_keys = _already_rated_keys(df)
    seen: set[int] = set()
    cards: list[DiscoveryCard] = []
    for genre_name in gap_genres:
        if len(cards) >= limit:
            break
        gid = name_to_id.get(genre_name)
        if gid is None:
            continue
        results = client.discover_by_genre(gid, sort_by="vote_average.desc", min_votes=DISCOVER_MIN_VOTES)
        why = f"You rarely rate {genre_name} movies — here's a well-regarded one"
        cards.extend(_filter_and_build(results, genre_map, rated_keys, why, seen, limit - len(cards)))
    return cards


def get_opposite_of_you_picks(
    df: pd.DataFrame, profile: TasteProfile, client: TMDBClient, limit: int = POOL_SIZE
) -> list[DiscoveryCard]:
    """Well-rated movies in genres you usually rate below your own average."""
    genre_map = client.get_genre_map()
    name_to_id = {name: gid for gid, name in genre_map.items()}
    disliked = sorted(
        (a for a in profile.genre_affinities.values() if a.score < 0),
        key=lambda a: a.score,
    )

    rated_keys = _already_rated_keys(df)
    seen: set[int] = set()
    cards: list[DiscoveryCard] = []
    for aff in disliked:
        if len(cards) >= limit:
            break
        gid = name_to_id.get(aff.name)
        if gid is None:
            continue
        results = client.discover_by_genre(gid, sort_by="vote_average.desc", min_votes=DISCOVER_MIN_VOTES)
        why = f"Well-rated {aff.name} movie — a genre you usually rate below your average"
        cards.extend(_filter_and_build(results, genre_map, rated_keys, why, seen, limit - len(cards)))
    return cards
