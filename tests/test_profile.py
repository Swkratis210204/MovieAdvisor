from imdb_parser import load_ratings
from taste_profile import build_profile

SAMPLE_PATH = "sample_ratings.csv"


def test_build_profile_overall_avg():
    df = load_ratings(SAMPLE_PATH)
    profile = build_profile(df)
    assert profile.overall_avg == df["your_rating"].mean()


def test_build_profile_genre_affinities_present():
    df = load_ratings(SAMPLE_PATH)
    profile = build_profile(df)
    assert "Drama" in profile.genre_affinities
    assert profile.genre_affinities["Drama"].count > 0


def test_build_profile_director_affinity_favors_high_rated_repeat_director():
    df = load_ratings(SAMPLE_PATH)
    profile = build_profile(df)
    # Christopher Nolan: rated 9, 9, 9 across three films -> should score well above average
    nolan = profile.director_affinities["Christopher Nolan"]
    assert nolan.count == 3
    assert nolan.avg_rating == 9.0
    assert nolan.score > 0


def test_top_directors_respects_min_films():
    df = load_ratings(SAMPLE_PATH)
    profile = build_profile(df)
    top = profile.top_directors(10, min_films=2)
    assert all(a.count >= 2 for a in top)
    names = {a.name for a in top}
    assert "Christopher Nolan" in names
    # A one-off director should not appear
    assert "Frank Darabont" not in names


def test_shrinkage_reduces_score_for_single_film_directors():
    df = load_ratings(SAMPLE_PATH)
    profile = build_profile(df)
    # Frank Darabont has 1 film rated 10 (well above average); shrinkage should
    # pull the score down compared to the raw (avg - overall_avg) difference.
    darabont = profile.director_affinities["Frank Darabont"]
    raw_diff = darabont.avg_rating - profile.overall_avg
    assert 0 < darabont.score < raw_diff
