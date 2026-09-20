"""Parsing and validation for IMDb ratings export CSVs."""
from __future__ import annotations

import io
import pandas as pd

# Canonical column name -> list of accepted variations (case-insensitive match)
COLUMN_ALIASES = {
    "const": ["const", "imdb id", "imdb_id", "id"],
    "your_rating": ["your rating", "your_rating", "rating"],
    "date_rated": ["date rated", "date_rated"],
    "title": ["title"],
    "title_type": ["title type", "title_type", "type"],
    "imdb_rating": ["imdb rating", "imdb_rating"],
    "runtime_mins": ["runtime (mins)", "runtime_mins", "runtime"],
    "year": ["year"],
    "genres": ["genres", "genre"],
    "num_votes": ["num votes", "num_votes", "votes"],
    "directors": ["directors", "director"],
}

REQUIRED = ["const", "your_rating", "title", "title_type"]


class CSVValidationError(ValueError):
    pass


def _build_rename_map(columns: list[str]) -> dict[str, str]:
    lower_to_actual = {c.strip().lower(): c for c in columns}
    rename_map = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in lower_to_actual:
                rename_map[lower_to_actual[alias]] = canonical
                break
    return rename_map


def load_ratings(file_or_buffer) -> pd.DataFrame:
    """Load and normalize an IMDb ratings export.

    Accepts a file path, file-like object, or bytes.
    Returns a DataFrame with canonical column names, filtered to movies only.
    Raises CSVValidationError if required columns are missing.
    """
    if isinstance(file_or_buffer, (bytes, bytearray)):
        file_or_buffer = io.BytesIO(file_or_buffer)

    try:
        df = pd.read_csv(file_or_buffer)
    except Exception as e:
        raise CSVValidationError(f"Could not read CSV file: {e}") from e

    if df.empty:
        raise CSVValidationError("The CSV file is empty.")

    rename_map = _build_rename_map(list(df.columns))
    df = df.rename(columns=rename_map)

    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise CSVValidationError(
            "Missing required column(s): "
            + ", ".join(missing)
            + ". Make sure you uploaded an IMDb 'ratings.csv' export."
        )

    # Fill in optional columns if absent so downstream code can rely on them
    for col in COLUMN_ALIASES:
        if col not in df.columns:
            df[col] = pd.NA

    # Filter to movies only (Title Type == "movie", case-insensitive)
    df["title_type"] = df["title_type"].astype(str).str.strip()
    df = df[df["title_type"].str.lower() == "movie"].copy()

    if df.empty:
        raise CSVValidationError(
            "No rows with Title Type == 'movie' were found in this file."
        )

    # Clean numeric columns
    df["your_rating"] = pd.to_numeric(df["your_rating"], errors="coerce")
    df["imdb_rating"] = pd.to_numeric(df["imdb_rating"], errors="coerce")
    df["runtime_mins"] = pd.to_numeric(df["runtime_mins"], errors="coerce")
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["num_votes"] = pd.to_numeric(
        df["num_votes"].astype(str).str.replace(",", "", regex=False),
        errors="coerce",
    )

    df = df.dropna(subset=["your_rating", "const"])
    df["your_rating"] = df["your_rating"].astype(float)

    # Clean string columns
    df["const"] = df["const"].astype(str).str.strip()
    df["title"] = df["title"].astype(str).str.strip()
    df["genres"] = df["genres"].fillna("").astype(str)
    df["directors"] = df["directors"].fillna("").astype(str)

    df = df.drop_duplicates(subset=["const"]).reset_index(drop=True)

    return df


def split_list_field(value: str) -> list[str]:
    """Split a comma-separated field like Genres or Directors into a clean list."""
    if value is None or (not isinstance(value, (list, tuple)) and pd.isna(value)):
        return []
    if not value:
        return []
    return [v.strip() for v in str(value).split(",") if v.strip()]
