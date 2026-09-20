import io

import pandas as pd
import pytest

from imdb_parser import CSVValidationError, load_ratings, split_list_field

SAMPLE_PATH = "sample_ratings.csv"


def test_load_sample_ratings_filters_to_movies_only():
    df = load_ratings(SAMPLE_PATH)
    assert len(df) == 20
    assert (df["title_type"].str.lower() == "movie").all()


def test_load_ratings_normalizes_column_names():
    df = load_ratings(SAMPLE_PATH)
    expected_cols = {"const", "your_rating", "title", "title_type", "genres", "directors"}
    assert expected_cols.issubset(set(df.columns))


def test_load_ratings_excludes_non_movie_rows():
    csv_data = (
        "Const,Your Rating,Title,Title Type,Genres,Directors\n"
        "tt0001,8,Movie A,Movie,Drama,Someone\n"
        "tt0002,9,Show B,TV Series,Drama,Someone Else\n"
    )
    df = load_ratings(io.BytesIO(csv_data.encode("utf-8")))
    assert len(df) == 1
    assert df.iloc[0]["title"] == "Movie A"


def test_load_ratings_handles_column_variations():
    csv_data = (
        "imdb_id,rating,title,type,genre,director\n"
        "tt0001,7,Movie A,Movie,Drama,Someone\n"
    )
    df = load_ratings(io.BytesIO(csv_data.encode("utf-8")))
    assert len(df) == 1
    assert df.iloc[0]["your_rating"] == 7.0


def test_load_ratings_missing_required_columns_raises():
    csv_data = "Title,Genres\nMovie A,Drama\n"
    with pytest.raises(CSVValidationError):
        load_ratings(io.BytesIO(csv_data.encode("utf-8")))


def test_load_ratings_drops_rows_with_missing_rating():
    csv_data = (
        "Const,Your Rating,Title,Title Type\n"
        "tt0001,,Movie A,Movie\n"
        "tt0002,8,Movie B,Movie\n"
    )
    df = load_ratings(io.BytesIO(csv_data.encode("utf-8")))
    assert len(df) == 1
    assert df.iloc[0]["title"] == "Movie B"


def test_load_ratings_empty_file_raises():
    with pytest.raises(CSVValidationError):
        load_ratings(io.BytesIO(b""))


def test_split_list_field():
    assert split_list_field("Drama, Crime, Thriller") == ["Drama", "Crime", "Thriller"]
    assert split_list_field("") == []
    assert split_list_field(None) == []
    assert split_list_field(pd.NA) == []
