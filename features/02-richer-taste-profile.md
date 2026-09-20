# Feature: Richer taste profile (clickable top movies, more info)

## Current state
"Your Taste Profile" (`app.py`, after upload) shows: overall average rating, IMDb average for the same films, a top-genres table, a top-directors table, and a rating-distribution bar chart. All aggregate stats — no individual movies are shown or linked anywhere in this section.

## What this feature adds
A "Your Top Movies" section, showing your actual highest-rated movies as clickable cards (poster, title, year, your rating, link to IMDb) — similar visual treatment to the recommendation cards, but pulled from your own ratings instead of TMDB suggestions.

Possible additions once that exists:
- **Decade breakdown** — a bar chart of your ratings by decade, showing whether you skew toward classics or new releases.
- **Runtime preference** — average runtime of movies you rate highly vs. poorly.
- **"Rated but forgotten" list** — movies you rated years ago you might want to revisit, sorted by oldest `Date Rated`.
- **Genre radar/spider chart** — visual alternative to the current genre table.

## Why this might be worth doing
Right now the profile section is all numbers and tables — it doesn't feel like "your" list the way the recommendation cards do. Seeing your own top movies as the same kind of poster-card makes the profile section feel like part of the same product, not just a stats readout, and gives you something to click through to IMDb directly from your own history.

## Implementation approach
- We don't currently fetch TMDB data (poster, etc.) for the user's *own* rated movies — only for recommendation candidates. This needs a small new function, e.g. `enrich_top_rated(df, client, n=12)` in `recommender.py`, that resolves IMDb IDs → TMDB IDs → poster/details for just the top N rated movies (reuses `TMDBClient.find_by_imdb_id` + `get_movie_full`, same pattern as the existing pipeline).
- Render with the same card layout already used for recommendations in `app.py` (`st.columns` + `st.container(border=True)`), so it looks consistent.
- This needs API calls and therefore a TMDB key — same key already entered in the sidebar, no new key needed. Worth caching aggressively since the same movies get re-fetched on every rerun otherwise (the existing `DiskCache` already covers this for free).

## Effort estimate
Small-medium. Mostly reuses existing patterns (TMDB enrichment, card rendering) rather than introducing new architecture.

## Open questions
- Show all-time top movies, or let the user pick a count (top 5/10/20)?
- Worth a "refresh" button, or just compute this every time the CSV loads (small extra API cost on every upload)?
