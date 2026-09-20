# Feature: Discovery / explore mode

## What
A separate "Explore" tab with movies not tied to your rating history: trending now, genres you rarely rate, and "opposite of you" picks (well-rated movies in genres/directors you usually rate below average).

## Decisions
- Build all three lenses (trending, genre-gap, opposite-of-you) — not just trending.
- Excludes already-rated movies, same as the main pipeline.

## How
New simple functions (direct TMDB `/trending` and `/discover` calls, no scoring machinery needed) in a new `discovery.py`. Same card layout as recommendations, added as a second `st.tabs(...)` entry in `app.py`.
