"""Streamlit app: recommend your next 10 movies from an IMDb ratings export."""
from __future__ import annotations

import os

import pandas as pd
import sentry_sdk
import streamlit as st
from dotenv import load_dotenv

from discovery import get_genre_gap_picks, get_opposite_of_you_picks, get_trending_picks
from imdb_parser import CSVValidationError, load_ratings, split_list_field
from llm_rewrite import DEFAULT_DAILY_LIMIT, daily_limit_reached, get_daily_usage, rewrite_why
from taste_profile import build_profile
from recommender import recommend
from tmdb_client import TMDBClient, TMDBError

load_dotenv()

# Error tracking only (no tracing/profiling/logs — not needed at this app's
# scale, and no PII/IP capture, to stay consistent with the app's own
# "no visitor tracking" privacy promise below). No-op if SENTRY_DSN isn't set.
sentry_sdk.init(dsn=os.getenv("SENTRY_DSN"), send_default_pii=False)

st.set_page_config(page_title="Next 10 Movies", page_icon="🎬", layout="wide")

# --- Optional privacy-friendly analytics (Umami) -----------------------------
# Cookie-free, no PII. Only embedded once per session (not on every Streamlit
# rerun/widget interaction) so it counts visits, not clicks. Reads the real
# top-level URL via window.parent since the tracking script otherwise only
# sees the sandboxed iframe Streamlit renders it into. No-op if unset.
umami_website_id = os.getenv("UMAMI_WEBSITE_ID")
if umami_website_id and not st.session_state.get("_umami_tracked"):
    st.session_state["_umami_tracked"] = True
    st.components.v1.html(
        f"""
        <script>
        (function() {{
            var s = document.createElement('script');
            s.defer = true;
            s.src = 'https://cloud.umami.is/script.js';
            s.setAttribute('data-website-id', '{umami_website_id}');
            s.setAttribute('data-auto-track', 'false');
            s.onload = function() {{
                if (window.umami) {{
                    window.umami.track(function(props) {{
                        return Object.assign({{}}, props, {{
                            url: window.parent.location.pathname + window.parent.location.search,
                            referrer: window.parent.document.referrer,
                        }});
                    }});
                }}
            }};
            document.head.appendChild(s);
        }})();
        </script>
        """,
        height=0,
        width=0,
    )

# --- Optional access gate ---------------------------------------------------
# If APP_PASSWORD is set on the server, visitors must enter it once per session
# before using the app. Leave APP_PASSWORD unset to keep the app fully open.
app_password = os.getenv("APP_PASSWORD")
if app_password and not st.session_state.get("authenticated"):
    st.title("🎬 Next 10 Movies")
    with st.form("password_gate"):
        entered = st.text_input("This app is password-protected. Enter the password to continue:", type="password")
        submitted = st.form_submit_button("Enter")
    if submitted:
        if entered.strip() == app_password.strip():
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    st.stop()

st.title("🎬 Next 10 Movies")
st.caption("Upload your IMDb ratings export and get a personalized watchlist powered by TMDB.")


uploaded = st.file_uploader("Upload your IMDb ratings.csv export", type=["csv"])

with st.expander("Don't know how to get your IMDb ratings export?"):
    st.markdown(
        """
1. Go to [imdb.com](https://www.imdb.com) and sign in to your account.
2. Click your name/profile icon (top right) and select **Your Ratings**.
3. On the Your Ratings page, click the **⋯** (more) menu near the top right of the list.
4. Select **Export**.
5. IMDb will download a file named `ratings.csv` — that's the file to upload above.
        """
    )

use_sample = st.checkbox(
    "Use bundled sample_ratings.csv instead (for demo/testing)",
    value=False,
    disabled=uploaded is not None,
    help="Unavailable while a file is uploaded — remove the uploaded file to use sample data instead."
    if uploaded is not None
    else None,
)
if uploaded is not None:
    use_sample = False

if use_sample:
    if st.session_state.get("ratings_source") != "sample":
        try:
            st.session_state["ratings_df"] = load_ratings("sample_ratings.csv")
            st.session_state["ratings_source"] = "sample"
        except CSVValidationError as e:
            st.error(str(e))
elif uploaded is not None:
    # Keyed by (name, size) so re-selecting the same file doesn't re-parse it,
    # but a different file does.
    upload_key = (uploaded.name, uploaded.size)
    if st.session_state.get("ratings_source") != upload_key:
        try:
            st.session_state["ratings_df"] = load_ratings(uploaded)
            st.session_state["ratings_source"] = upload_key
        except CSVValidationError as e:
            st.error(str(e))

# Cached in session_state (not just the widget's return value) so a browser
# reload — which resets the file_uploader widget but keeps the Streamlit
# session — doesn't lose the already-parsed data.
df = st.session_state.get("ratings_df")

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

def _movies_for(list_col: str, values: list[str]) -> pd.DataFrame:
    values_set = set(values)
    mask = df[list_col].apply(lambda v: bool(values_set & set(split_list_field(v))))
    return (
        df.loc[mask, ["title", "year", "your_rating"]]
        .sort_values("your_rating", ascending=False)
        .rename(columns={"title": "Title", "year": "Year", "your_rating": "Your Rating"})
    )


pcol1, pcol2 = st.columns(2)
with pcol1:
    st.subheader("Top genres")
    top_genres = profile.top_genres(8)
    if top_genres:
        st.caption("👇 Click the checkbox next to one or more genres to see which of your movies they are.")
        genre_df = pd.DataFrame(
            [{"Genre": a.name, "Avg Rating": round(a.avg_rating, 2), "Films": a.count} for a in top_genres]
        ).set_index("Genre")
        event = st.dataframe(
            genre_df,
            use_container_width=True,
            on_select="rerun",
            selection_mode="multi-row",
            key="genre_table",
        )
        selected_rows = event.selection.rows if event and event.selection else []
        if selected_rows:
            genre_names = [genre_df.index[i] for i in selected_rows]
            st.caption(f"Movies you rated in **{', '.join(genre_names)}**:")
            st.dataframe(_movies_for("genres", genre_names), use_container_width=True, hide_index=True)
    else:
        st.write("Not enough genre data.")

with pcol2:
    st.subheader("Top directors (2+ films)")
    top_directors = profile.top_directors(8, min_films=2)
    if top_directors:
        st.caption("👇 Click the checkbox next to one or more directors to see which of your movies they are.")
        dir_df = pd.DataFrame(
            [{"Director": a.name, "Avg Rating": round(a.avg_rating, 2), "Films": a.count} for a in top_directors]
        ).set_index("Director")
        event = st.dataframe(
            dir_df,
            use_container_width=True,
            on_select="rerun",
            selection_mode="multi-row",
            key="director_table",
        )
        selected_rows = event.selection.rows if event and event.selection else []
        if selected_rows:
            director_names = [dir_df.index[i] for i in selected_rows]
            st.caption(f"Movies you rated by **{', '.join(director_names)}**:")
            st.dataframe(_movies_for("directors", director_names), use_container_width=True, hide_index=True)
    else:
        st.write("No director has 2+ films yet.")

st.subheader("Rating distribution")
dist = df["your_rating"].value_counts().sort_index()
st.bar_chart(dist, use_container_width=True)
st.caption("👇 Pick one or more rating values to see which of your movies they are.")
rating_options = sorted(dist.index, reverse=True)
picked_ratings = st.multiselect(
    "See the movies behind a bar",
    options=rating_options,
    format_func=lambda r: f"Rated {r:g} — {dist[r]} movie(s)",
    placeholder="Choose one or more ratings...",
)
if picked_ratings:
    st.caption(f"Movies you rated **{', '.join(f'{r:g}' for r in picked_ratings)}**:")
    rated_movies = (
        df.loc[df["your_rating"].isin(picked_ratings), ["title", "year", "your_rating"]]
        .sort_values(["your_rating", "title"], ascending=[False, True])
        .rename(columns={"title": "Title", "year": "Year", "your_rating": "Your Rating"})
    )
    st.dataframe(rated_movies, use_container_width=True, hide_index=True)

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
    live="300ms",
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

# --- Optional: LLM rewrite of "why" lines (free, open-source model via Groq) ---
st.sidebar.header("Why-text rewrite (optional)")
server_groq_key = os.getenv("GROQ_API_KEY")
groq_cap_reached = bool(server_groq_key) and daily_limit_reached()
use_llm_rewrite = st.sidebar.checkbox(
    "Rewrite 'why' lines with a free open-source LLM",
    value=False,
    disabled=not server_groq_key or groq_cap_reached,
    help=(
        "Requires GROQ_API_KEY to be set on the server. Get a free key at console.groq.com."
        if not server_groq_key
        else "Today's shared rewrite quota is used up — resets at midnight UTC."
        if groq_cap_reached
        else "Rewrites the recommendation reason in more natural prose using an open-weight "
        "model hosted free via Groq. Off by default; the app works fully without it."
    ),
)
if server_groq_key:
    st.sidebar.caption(
        f"Shared rewrite usage today: {get_daily_usage()}/{DEFAULT_DAILY_LIMIT} "
        "(this quota is shared across all visitors, to keep the shared key's cost capped)."
    )

# --- Recommendations & Explore tabs ----------------------------------------
tab1, tab2 = st.tabs(["Recommendations", "Explore"])

with tab1:
    # --- Recommendations -----------------------------------------------------
    st.header("Get Recommendations")

    if not api_key:
        st.info(
            "Enter a TMDB API key in the sidebar to enable recommendations (get one free at "
            "themoviedb.org/settings/api), or set TMDB_API_KEY in a .env file if you're running this locally."
        )

    if st.button("Find my next 10 movies", type="primary"):
        if not api_key:
            st.warning("Enter a TMDB API key in the sidebar first.")
            st.stop()

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
        st.session_state["shown_count"] = 10

    all_results = st.session_state.get("results")

    if all_results:
        shown_count = min(st.session_state.get("shown_count", 10), len(all_results))
        results = all_results[:shown_count]

        st.subheader(f"Your Next {len(results)} Movies")

        profile_summary = (
            f"Average rating {profile.overall_avg:.1f}. "
            f"Top genres: {', '.join(a.name for a in profile.top_genres(3))}. "
            f"Top directors: {', '.join(a.name for a in profile.top_directors(3))}."
        )

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
                        why_text = c.why
                        if use_llm_rewrite and server_groq_key:
                            why_text = rewrite_why(c.why, c.title, profile_summary, server_groq_key)
                        st.write(f"*{why_text}*")
                        st.markdown(f"[View on IMDb]({c.imdb_url})")

        if shown_count < len(all_results):
            if st.button("Show me 10 more"):
                st.session_state["shown_count"] = shown_count + 10
                st.rerun()
        else:
            st.caption("That's all the recommendations available with your current filters.")

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

with tab2:
    st.header("Explore")
    st.caption(
        "Movies outside your rating history: what's trending, genres you rarely rate, "
        "and well-rated movies in genres you usually don't love."
    )

    if not api_key:
        st.info(
            "Enter a TMDB API key in the sidebar to enable exploring (get one free at "
            "themoviedb.org/settings/api), or set TMDB_API_KEY in a .env file if you're running this locally."
        )

    def _render_discovery_cards(cards) -> None:
        if not cards:
            st.write("No picks found.")
            return
        cols = st.columns(2)
        for i, c in enumerate(cards):
            with cols[i % 2]:
                with st.container(border=True):
                    inner_col1, inner_col2 = st.columns([1, 2])
                    with inner_col1:
                        poster = TMDBClient.poster_url(c.poster_path)
                        if poster:
                            st.image(poster, use_container_width=True)
                    with inner_col2:
                        st.markdown(f"### {c.title} ({c.year or 'N/A'})")
                        st.write(", ".join(c.genres) or "N/A")
                        st.write(f"TMDB rating: {c.vote_average:.1f}/10 ({c.vote_count:,} votes)")
                        st.write(f"*{c.why}*")
                        st.markdown(f"[View on TMDB]({c.tmdb_url})")

    if st.button("Load explore picks", type="primary", disabled=not api_key):
        client = TMDBClient(api_key)
        with st.spinner("Fetching trending, genre-gap, and opposite-of-you picks..."):
            try:
                st.session_state["explore_trending"] = get_trending_picks(df, client)
                st.session_state["explore_genre_gap"] = get_genre_gap_picks(df, profile, client)
                st.session_state["explore_opposite"] = get_opposite_of_you_picks(df, profile, client)
            except TMDBError as e:
                st.error(f"TMDB error: {e}")
                st.stop()

    if "explore_trending" in st.session_state:
        st.subheader("Trending now")
        _render_discovery_cards(st.session_state["explore_trending"])

        st.subheader("Genres you rarely rate")
        _render_discovery_cards(st.session_state["explore_genre_gap"])

        st.subheader("Opposite of you")
        _render_discovery_cards(st.session_state["explore_opposite"])

# --- Footer: TMDB attribution + privacy note + disclaimer -------------------
st.divider()
footer_col1, footer_col2 = st.columns([3, 2])
with footer_col1:
    st.caption(
        "This product uses the [TMDB API](https://www.themoviedb.org/) but is not endorsed or "
        "certified by TMDB."
    )
with footer_col2:
    st.caption(
        "Questions or bugs? [Open an issue on GitHub]"
        "(https://github.com/Swkratis210204/MovieAdvisor/issues)."
    )
st.caption(
    "This is a personal, hobby project provided as-is, with no warranty of any kind. Use at "
    "your own risk."
)

with st.expander("Privacy & data handling"):
    st.markdown(
        """
- **Your uploaded ratings CSV** is kept only in this browser session's server-side memory —
  never written to disk, never stored in a database, never shared with other visitors. It's
  gone as soon as the session ends (e.g. closing the tab, or the server restarting).
- **Your TMDB API key** (and optional Groq key) is used only to make requests on your behalf
  for this session. It is never logged, saved, or sent anywhere except the respective API
  (TMDB, and Groq only if you enable the "why" rewrite).
- **Third parties involved:** [TMDB](https://www.themoviedb.org/) for movie data (using your
  own key), optionally [Groq](https://groq.com/) if you turn on the LLM rewrite feature, and
  [Umami](https://umami.is) for anonymous visit analytics.
- **No cookies.** Visit analytics (Umami) are cookie-free and don't identify you individually —
  no cross-site tracking, no fingerprinting, no personal data collected.
- Questions, or want something about how this works clarified? [Open an issue on GitHub](https://github.com/Swkratis210204/MovieAdvisor/issues).
        """
    )
