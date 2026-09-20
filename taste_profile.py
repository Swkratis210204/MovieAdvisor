"""Taste profile: per-genre / per-director affinity scoring from rated movies."""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from imdb_parser import split_list_field

# Shrinkage constant for small-sample affinity (higher = more shrinkage toward 0)
SHRINKAGE_K = 3.0


@dataclass
class Affinity:
    name: str
    count: int
    avg_rating: float
    score: float  # shrunk, mean-centered affinity


@dataclass
class TasteProfile:
    overall_avg: float
    imdb_avg_for_my_films: float
    genre_affinities: dict[str, Affinity] = field(default_factory=dict)
    director_affinities: dict[str, Affinity] = field(default_factory=dict)

    def top_genres(self, n: int = 5) -> list[Affinity]:
        return sorted(self.genre_affinities.values(), key=lambda a: a.score, reverse=True)[:n]

    def top_directors(self, n: int = 5, min_films: int = 2) -> list[Affinity]:
        eligible = [a for a in self.director_affinities.values() if a.count >= min_films]
        return sorted(eligible, key=lambda a: a.score, reverse=True)[:n]


def _affinity_table(df: pd.DataFrame, list_col: str, overall_avg: float) -> dict[str, Affinity]:
    """Explode a comma-separated column and compute shrunk affinity per value."""
    rows = []
    for _, row in df.iterrows():
        for item in split_list_field(row[list_col]):
            rows.append((item, row["your_rating"]))

    if not rows:
        return {}

    exploded = pd.DataFrame(rows, columns=["item", "rating"])
    grouped = exploded.groupby("item")["rating"].agg(["mean", "count"])

    affinities = {}
    for item, r in grouped.iterrows():
        count = int(r["count"])
        avg = float(r["mean"])
        # Shrink toward overall average for small sample sizes
        shrunk_score = (count / (count + SHRINKAGE_K)) * (avg - overall_avg)
        affinities[item] = Affinity(name=item, count=count, avg_rating=avg, score=shrunk_score)

    return affinities


def build_profile(df: pd.DataFrame) -> TasteProfile:
    """Build a TasteProfile from a cleaned ratings DataFrame (movies only)."""
    overall_avg = float(df["your_rating"].mean())

    imdb_ratings = df["imdb_rating"].dropna()
    imdb_avg = float(imdb_ratings.mean()) if not imdb_ratings.empty else float("nan")

    genre_affinities = _affinity_table(df, "genres", overall_avg)
    director_affinities = _affinity_table(df, "directors", overall_avg)

    return TasteProfile(
        overall_avg=overall_avg,
        imdb_avg_for_my_films=imdb_avg,
        genre_affinities=genre_affinities,
        director_affinities=director_affinities,
    )
