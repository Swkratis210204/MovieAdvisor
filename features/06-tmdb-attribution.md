# Go-live: TMDB attribution (compliance, not optional)

## What
TMDB's API terms of use require displaying their logo and the attribution line "This product uses the TMDB API but is not endorsed or certified by TMDB" wherever TMDB data is shown. This app shows TMDB data (posters, ratings, titles) throughout the Recommendations and Explore tabs and currently has no attribution anywhere.

## How
1. Download TMDB's official logo/attribution assets from their brand guidelines page (themoviedb.org).
2. Add the logo + attribution text to the app footer (visible on every page, not buried in an expander) — e.g. `st.caption` or `st.markdown` at the bottom of `app.py`, outside the tabs so it always shows.
3. Also add a short mention in `README.md` since the repo itself is public.

This is the one item in this whole list that's a legal/ToS requirement rather than a nice-to-have — do it before any real traffic.
