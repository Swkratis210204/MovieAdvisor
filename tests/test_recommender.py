from imdb_parser import load_ratings
from taste_profile import Affinity, TasteProfile, build_profile
from recommender import (
    Candidate,
    apply_diversity_filter,
    apply_sidebar_filters,
    score_candidates,
    select_seeds,
)

SAMPLE_PATH = "sample_ratings.csv"


def make_candidate(tmdb_id, title, genres=None, directors=None, vote_average=7.0,
                    vote_count=10000, runtime=120, year=2015, collection_id=None,
                    frequency_score=1.0, recommended_by=None):
    return Candidate(
        tmdb_id=tmdb_id,
        imdb_id=f"tt{tmdb_id:07d}",
        title=title,
        year=year,
        runtime=runtime,
        genres=genres or [],
        directors=directors or [],
        vote_average=vote_average,
        vote_count=vote_count,
        poster_path=None,
        collection_id=collection_id,
        recommended_by=recommended_by or [("Seed Movie", 1.0)],
        frequency_score=frequency_score,
    )


def test_select_seeds_filters_by_min_rating_and_caps_count():
    df = load_ratings(SAMPLE_PATH)
    seeds = select_seeds(df)
    assert (seeds["your_rating"] >= 8).all()
    assert len(seeds) <= 40


def test_apply_sidebar_filters_min_votes():
    candidates = [make_candidate(1, "Low Votes", vote_count=100)]
    filtered = apply_sidebar_filters(candidates, None, None, [], [])
    assert filtered == []


def test_apply_sidebar_filters_runtime_and_year():
    candidates = [
        make_candidate(1, "Too Long", runtime=200, year=2010),
        make_candidate(2, "Too Old", runtime=100, year=1950),
        make_candidate(3, "Just Right", runtime=100, year=2010),
    ]
    filtered = apply_sidebar_filters(candidates, max_runtime=150, min_year=1990, include_genres=[], exclude_genres=[])
    titles = {c.title for c in filtered}
    assert titles == {"Just Right"}


def test_apply_sidebar_filters_include_exclude_genres():
    candidates = [
        make_candidate(1, "Action Movie", genres=["Action"]),
        make_candidate(2, "Drama Movie", genres=["Drama"]),
        make_candidate(3, "Both", genres=["Action", "Drama"]),
    ]
    filtered = apply_sidebar_filters(candidates, None, None, include_genres=["Action"], exclude_genres=[])
    titles = {c.title for c in filtered}
    assert titles == {"Action Movie", "Both"}

    filtered = apply_sidebar_filters(candidates, None, None, include_genres=[], exclude_genres=["Drama"])
    titles = {c.title for c in filtered}
    assert titles == {"Action Movie"}


def test_score_candidates_rewards_genre_and_director_affinity():
    profile = TasteProfile(
        overall_avg=7.0,
        imdb_avg_for_my_films=7.5,
        genre_affinities={"Sci-Fi": Affinity("Sci-Fi", 5, 9.0, 1.5)},
        director_affinities={"Christopher Nolan": Affinity("Christopher Nolan", 3, 9.0, 1.8)},
    )
    matching = make_candidate(1, "Matches Taste", genres=["Sci-Fi"], directors=["Christopher Nolan"])
    non_matching = make_candidate(2, "No Match", genres=["Romance"], directors=["Unknown Director"])

    scored = score_candidates([matching, non_matching], profile)
    scored_by_title = {c.title: c for c in scored}
    assert scored_by_title["Matches Taste"].score > scored_by_title["No Match"].score
    assert scored[0].title == "Matches Taste"


def test_build_why_mentions_seed_and_genre():
    profile = TasteProfile(
        overall_avg=7.0,
        imdb_avg_for_my_films=7.5,
        genre_affinities={"Sci-Fi": Affinity("Sci-Fi", 5, 9.0, 1.5)},
        director_affinities={},
    )
    c = make_candidate(1, "Test Movie", genres=["Sci-Fi"], recommended_by=[("Inception", 2.0)])
    scored = score_candidates([c], profile)
    assert "Inception" in scored[0].why
    assert "Sci-Fi" in scored[0].why


def test_apply_diversity_filter_caps_per_director():
    candidates = [
        make_candidate(i, f"Movie {i}", directors=["Same Director"], frequency_score=10 - i)
        for i in range(5)
    ]
    result = apply_diversity_filter(candidates, top_n=10)
    assert len(result) == 3


def test_apply_diversity_filter_caps_per_franchise():
    candidates = [
        make_candidate(i, f"Movie {i}", collection_id=99, frequency_score=10 - i)
        for i in range(5)
    ]
    result = apply_diversity_filter(candidates, top_n=10)
    assert len(result) == 3


def test_apply_diversity_filter_respects_top_n():
    candidates = [make_candidate(i, f"Movie {i}") for i in range(20)]
    result = apply_diversity_filter(candidates, top_n=10)
    assert len(result) == 10
