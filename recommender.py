"""Candidate generation, scoring, ranking, and diversity filtering."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

import pandas as pd

from taste_profile import TasteProfile
from tmdb_client import TMDBClient

# --- Tunables -------------------------------------------------------------
SEED_MIN_RATING = 8
SEED_MAX_COUNT = 40

SOURCE_WEIGHT_RECOMMENDATIONS = 1.0
SOURCE_WEIGHT_SIMILAR = 0.6

STAGE_B_CANDIDATE_LIMIT = 80  # how many raw candidates get the detail/credits fetch
MIN_VOTES = 500

SCORE_WEIGHT_FREQUENCY = 1.0
SCORE_WEIGHT_GENRE = 2.0
SCORE_WEIGHT_DIRECTOR = 2.5
SCORE_WEIGHT_QUALITY = 0.5

MAX_PER_DIRECTOR = 3
MAX_PER_FRANCHISE = 3

FINAL_TOP_N = 10
POOL_SIZE = 30  # fetch this many diversity-filtered candidates so "show 10 more" needs no extra API calls


@dataclass
class RawCandidate:
    tmdb_id: int
    title: str
    preliminary_score: float = 0.0
    recommended_by: list[tuple[str, float]] = field(default_factory=list)  # (seed_title, seed_weight)


@dataclass
class Candidate:
    tmdb_id: int
    imdb_id: str
    title: str
    year: Optional[int]
    runtime: Optional[int]
    genres: list[str]
    directors: list[str]
    vote_average: float
    vote_count: int
    poster_path: Optional[str]
    collection_id: Optional[int]
    recommended_by: list[tuple[str, float]]
    frequency_score: float = 0.0
    genre_affinity_score: float = 0.0
    director_affinity_score: float = 0.0
    quality_prior: float = 0.0
    score: float = 0.0
    why: str = ""

    @property
    def imdb_url(self) -> str:
        return f"https://www.imdb.com/title/{self.imdb_id}/"


def select_seeds(df: pd.DataFrame) -> pd.DataFrame:
    """Pick the source movies to fan out from: rating >= 8, capped to top N."""
    seeds = df[df["your_rating"] >= SEED_MIN_RATING].copy()
    if seeds.empty:
        # fall back to top-rated movies overall if nobody rated >= 8
        seeds = df.copy()
    seeds = seeds.sort_values("your_rating", ascending=False).head(SEED_MAX_COUNT)
    return seeds


def generate_candidates(
    seeds: pd.DataFrame,
    overall_avg: float,
    client: TMDBClient,
    progress_cb: Optional[Callable[[float, str], None]] = None,
) -> dict[int, RawCandidate]:
    """Fan out from seed movies via TMDB recommendations + similar endpoints."""
    raw: dict[int, RawCandidate] = {}
    n = len(seeds)
    for i, (_, seed_row) in enumerate(seeds.iterrows()):
        if progress_cb:
            progress_cb((i / max(n, 1)) * 0.5, f"Finding recommendations for {seed_row['title']}...")

        seed_weight = max(seed_row["your_rating"] - overall_avg, 0.1)
        found = client.find_by_imdb_id(seed_row["const"])
        if not found:
            continue
        seed_tmdb_id = found["id"]

        for source, weight in (
            (client.get_recommendations, SOURCE_WEIGHT_RECOMMENDATIONS),
            (client.get_similar, SOURCE_WEIGHT_SIMILAR),
        ):
            try:
                results = source(seed_tmdb_id)
            except Exception:
                continue
            for r in results:
                cid = r["id"]
                if cid == seed_tmdb_id:
                    continue
                entry = raw.setdefault(cid, RawCandidate(tmdb_id=cid, title=r.get("title", "")))
                entry.preliminary_score += seed_weight * weight
                entry.recommended_by.append((seed_row["title"], seed_weight))

    return raw


def enrich_and_filter_candidates(
    raw_candidates: dict[int, RawCandidate],
    rated_imdb_ids: set[str],
    client: TMDBClient,
    progress_cb: Optional[Callable[[float, str], None]] = None,
) -> list[Candidate]:
    """Fetch full details for the top raw candidates, drop already-watched ones."""
    top_raw = sorted(raw_candidates.values(), key=lambda c: c.preliminary_score, reverse=True)
    top_raw = top_raw[:STAGE_B_CANDIDATE_LIMIT]

    candidates: list[Candidate] = []
    n = len(top_raw)
    for i, rc in enumerate(top_raw):
        if progress_cb:
            progress_cb(0.5 + (i / max(n, 1)) * 0.4, f"Fetching details for {rc.title}...")
        try:
            full = client.get_movie_full(rc.tmdb_id)
        except Exception:
            continue
        if not full:
            continue

        imdb_id = (full.get("external_ids") or {}).get("imdb_id")
        if not imdb_id or imdb_id in rated_imdb_ids:
            continue

        directors = [
            crew["name"]
            for crew in (full.get("credits") or {}).get("crew", [])
            if crew.get("job") == "Director"
        ]
        genres = [g["name"] for g in full.get("genres", [])]
        collection = full.get("belongs_to_collection")
        release_date = full.get("release_date") or ""
        year = int(release_date[:4]) if release_date[:4].isdigit() else None

        candidates.append(
            Candidate(
                tmdb_id=rc.tmdb_id,
                imdb_id=imdb_id,
                title=full.get("title", rc.title),
                year=year,
                runtime=full.get("runtime"),
                genres=genres,
                directors=directors,
                vote_average=float(full.get("vote_average") or 0.0),
                vote_count=int(full.get("vote_count") or 0),
                poster_path=full.get("poster_path"),
                collection_id=(collection or {}).get("id"),
                recommended_by=rc.recommended_by,
                frequency_score=rc.preliminary_score,
            )
        )

    return candidates


def apply_sidebar_filters(
    candidates: list[Candidate],
    max_runtime: Optional[int],
    min_year: Optional[int],
    include_genres: list[str],
    exclude_genres: list[str],
) -> list[Candidate]:
    filtered = []
    for c in candidates:
        if c.vote_count < MIN_VOTES:
            continue
        if max_runtime and c.runtime and c.runtime > max_runtime:
            continue
        if min_year and c.year and c.year < min_year:
            continue
        if include_genres and not any(g in c.genres for g in include_genres):
            continue
        if exclude_genres and any(g in c.genres for g in exclude_genres):
            continue
        filtered.append(c)
    return filtered


def score_candidates(candidates: list[Candidate], profile: TasteProfile) -> list[Candidate]:
    if not candidates:
        return candidates

    max_freq = max((c.frequency_score for c in candidates), default=1.0) or 1.0

    for c in candidates:
        norm_freq = c.frequency_score / max_freq

        genre_score = sum(
            profile.genre_affinities[g].score for g in c.genres if g in profile.genre_affinities
        )
        director_score = sum(
            profile.director_affinities[d].score
            for d in c.directors
            if d in profile.director_affinities
        )
        quality_prior = (c.vote_average / 10.0) if c.vote_average else 0.0

        c.genre_affinity_score = genre_score
        c.director_affinity_score = director_score
        c.quality_prior = quality_prior

        c.score = (
            SCORE_WEIGHT_FREQUENCY * norm_freq
            + SCORE_WEIGHT_GENRE * genre_score
            + SCORE_WEIGHT_DIRECTOR * director_score
            + SCORE_WEIGHT_QUALITY * quality_prior
        )
        c.why = _build_why(c, profile)

    return sorted(candidates, key=lambda c: c.score, reverse=True)


def _build_why(c: Candidate, profile: TasteProfile) -> str:
    parts = []
    if c.recommended_by:
        sources = sorted(set(t for t, _ in c.recommended_by))
        sample = sources[:3]
        names = ", ".join(sample)
        more = f" and {len(sources) - 3} more" if len(sources) > 3 else ""
        parts.append(f"Recommended by {len(sources)} of your favorites ({names}{more})")

    liked_genres = [g for g in c.genres if profile.genre_affinities.get(g) and profile.genre_affinities[g].score > 0]
    if liked_genres:
        parts.append(f"matches your love of {', '.join(liked_genres[:2])}")

    liked_directors = [
        d for d in c.directors if profile.director_affinities.get(d) and profile.director_affinities[d].score > 0
    ]
    if liked_directors:
        parts.append(f"directed by {', '.join(liked_directors)}, whose work you rate highly")

    if not parts:
        parts.append(f"Highly rated on TMDB ({c.vote_average:.1f}/10)")

    return "; ".join(parts) + "."


def apply_diversity_filter(candidates: list[Candidate], top_n: int = FINAL_TOP_N) -> list[Candidate]:
    """Greedily pick top_n candidates, capping how many share a director or franchise."""
    selected: list[Candidate] = []
    director_counts: dict[str, int] = {}
    franchise_counts: dict[int, int] = {}

    for c in candidates:
        if len(selected) >= top_n:
            break

        director_blocked = any(director_counts.get(d, 0) >= MAX_PER_DIRECTOR for d in c.directors)
        franchise_blocked = c.collection_id is not None and franchise_counts.get(c.collection_id, 0) >= MAX_PER_FRANCHISE
        if director_blocked or franchise_blocked:
            continue

        selected.append(c)
        for d in c.directors:
            director_counts[d] = director_counts.get(d, 0) + 1
        if c.collection_id is not None:
            franchise_counts[c.collection_id] = franchise_counts.get(c.collection_id, 0) + 1

    return selected


def recommend(
    df: pd.DataFrame,
    profile: TasteProfile,
    client: TMDBClient,
    max_runtime: Optional[int] = None,
    min_year: Optional[int] = None,
    include_genres: Optional[list[str]] = None,
    exclude_genres: Optional[list[str]] = None,
    progress_cb: Optional[Callable[[float, str], None]] = None,
    pool_size: int = POOL_SIZE,
) -> list[Candidate]:
    """End-to-end pipeline: seeds -> raw candidates -> enriched -> filtered -> scored -> diverse pool.

    Returns up to `pool_size` candidates (diversity rule applied across the whole pool), so callers
    can page through them (e.g. 10 at a time) without re-fetching from TMDB.
    """
    seeds = select_seeds(df)
    rated_imdb_ids = set(df["const"])

    raw = generate_candidates(seeds, profile.overall_avg, client, progress_cb)
    candidates = enrich_and_filter_candidates(raw, rated_imdb_ids, client, progress_cb)

    if progress_cb:
        progress_cb(0.95, "Scoring and ranking...")

    candidates = apply_sidebar_filters(
        candidates, max_runtime, min_year, include_genres or [], exclude_genres or []
    )
    candidates = score_candidates(candidates, profile)
    top = apply_diversity_filter(candidates, pool_size)

    if progress_cb:
        progress_cb(1.0, "Done.")

    return top
