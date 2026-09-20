"""Streamlit app: recommend your next 10 movies from an IMDb ratings export."""
from __future__ import annotations

import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from imdb_parser import CSVValidationError, load_ratings, split_list_field
from taste_profile import build_profile
from recommender import recommend
from tmdb_client import TMDBClient, TMDBError

load_dotenv()

st.set_page_config(page_title="Next 10 Movies", page_icon="🎬", layout="wide")
st.title("🎬 Next 10 Movies")
st.caption("Upload your IMDb ratings export and get a personalized watchlist powered by TMDB.")


uploaded = st.file_uploader("Upload your IMDb ratings.csv export", type=["csv"])

use_sample = st.checkbox("Use bundled sample_ratings.csv instead (for demo/testing)", value=False)

df = None
if use_sample:
    try:
        df = load_ratings("sample_ratings.csv")
    except CSVValidationError as e:
        st.error(str(e))
elif uploaded is not None:
    try:
        df = load_ratings(uploaded)
    except CSVValidationError as e:
        st.error(str(e))

if df is None:
    st.info("Upload a CSV to get started. Export it from IMDb: Your Ratings → ... → Export.")
    st.stop()

st.success(f"Loaded {len(df)} rated movies.")

profile = build_profile(df)

# --- Taste profile section -------------------------------------------------
st.header("Your Taste Profile")

col1, col2, col3 = st.columns(3)
col1.metric("Your average rating", f"{profile.overall_avg:.2f}")
if not pd.isna(profile.imdb_avg_for_my_films):
    delta = profile.overall_avg - profile.imdb_avg_for_my_films
    col2.metric("IMDb average (same films)", f"{profile.imdb_avg_for_my_films:.2f}", delta=f"{delta:+.2f}")
else:
    col2.metric("IMDb average (same films)", "N/A")
col3.metric("Movies rated", len(df))

pcol1, pcol2 = st.columns(2)
with pcol1:
    st.subheader("Top genres")
    top_genres = profile.top_genres(8)
    if top_genres:
        genre_df = pd.DataFrame(
            [{"Genre": a.name, "Avg Rating": round(a.avg_rating, 2), "Films": a.count} for a in top_genres]
        ).set_index("Genre")
        st.dataframe(genre_df, use_container_width=True)
    else:
        st.write("Not enough genre data.")

with pcol2:
    st.subheader("Top directors (2+ films)")
    top_directors = profile.top_directors(8, min_films=2)
    if top_directors:
        dir_df = pd.DataFrame(
            [{"Director": a.name, "Avg Rating": round(a.avg_rating, 2), "Films": a.count} for a in top_directors]
        ).set_index("Director")
        st.dataframe(dir_df, use_container_width=True)
    else:
        st.write("No director has 2+ films yet.")

st.subheader("Rating distribution")
dist = df["your_rating"].value_counts().sort_index()
st.bar_chart(dist)

# --- Sidebar filters ---------------------------------------------------
st.sidebar.header("Filters")
max_runtime = st.sidebar.slider("Max runtime (minutes)", 60, 240, 180, step=10)
min_year = st.sidebar.number_input("Minimum release year", min_value=1900, max_value=2030, value=1970, step=1)

all_genres = sorted({g for genres in df["genres"] for g in split_list_field(genres)})
include_genres = st.sidebar.multiselect("Include genres (any of)", all_genres)
exclude_genres = st.sidebar.multiselect("Exclude genres", all_genres)

# --- TMDB API key ---------------------------------------------------------
st.sidebar.header("TMDB API Key")
server_api_key = os.getenv("TMDB_API_KEY")
user_api_key = st.sidebar.text_input(
    "Your TMDB API key",
    type="password",
    value="",
    help=(
        "Free to get at themoviedb.org/settings/api. Used only for this browser session "
        "to call TMDB on your behalf — it is never saved to disk or shared with other users."
    ),
)
st.sidebar.caption(
    "TMDB API keys are 100% free, no credit card or billing info required. "
    "Sign up at [themoviedb.org/settings/api](https://www.themoviedb.org/settings/api) "
    "to get yours in under a minute."
)
api_key = user_api_key.strip() or server_api_key

# --- Recommendations -----------------------------------------------------
st.header("Get Recommendations")

if not api_key:
    st.error(
        "A TMDB API key is required. Enter your own key in the sidebar (get one free at "
        "themoviedb.org/settings/api), or set TMDB_API_KEY in a .env file if you're running this locally."
    )
    st.stop()

if st.button("Find my next 10 movies", type="primary"):
    progress_bar = st.progress(0.0)
    status_text = st.empty()

    def progress_cb(frac: float, message: str) -> None:
        progress_bar.progress(min(max(frac, 0.0), 1.0))
        status_text.text(message)

    try:
        client = TMDBClient(api_key)
        results = recommend(
            df,
            profile,
            client,
            max_runtime=max_runtime,
            min_year=min_year,
            include_genres=include_genres,
            exclude_genres=exclude_genres,
            progress_cb=progress_cb,
        )
    except TMDBError as e:
        st.error(f"TMDB error: {e}")
        st.stop()
    finally:
        progress_bar.empty()
        status_text.empty()

    if not results:
        st.warning("No recommendations found with the current filters. Try loosening them.")
        st.stop()

    st.session_state["results"] = results

results = st.session_state.get("results")

if results:
    st.subheader(f"Your Next {len(results)} Movies")

    cols = st.columns(2)
    for i, c in enumerate(results):
        with cols[i % 2]:
            with st.container(border=True):
                inner_col1, inner_col2 = st.columns([1, 2])
                with inner_col1:
                    poster = TMDBClient.poster_url(c.poster_path)
                    if poster:
                        st.image(poster, use_container_width=True)
                with inner_col2:
                    st.markdown(f"### {c.title} ({c.year or 'N/A'})")
                    runtime_str = f"{c.runtime} min" if c.runtime else "Runtime N/A"
                    st.write(f"{runtime_str} · {', '.join(c.genres) or 'N/A'}")
                    st.write(f"TMDB rating: {c.vote_average:.1f}/10 ({c.vote_count:,} votes)")
                    st.write(f"*{c.why}*")
                    st.markdown(f"[View on IMDb]({c.imdb_url})")

    export_df = pd.DataFrame(
        [
            {
                "Title": c.title,
                "Year": c.year,
                "Runtime": c.runtime,
                "Genres": ", ".join(c.genres),
                "Directors": ", ".join(c.directors),
                "TMDB Rating": c.vote_average,
                "IMDb URL": c.imdb_url,
                "Why": c.why,
                "Score": round(c.score, 3),
            }
            for c in results
        ]
    )
    csv_bytes = export_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download recommendations as CSV",
        data=csv_bytes,
        file_name="recommendations.csv",
        mime="text/csv",
    )
