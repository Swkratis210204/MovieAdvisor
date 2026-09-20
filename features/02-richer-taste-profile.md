# Feature: Richer taste profile

## What
Show your actual top-rated movies as clickable poster cards (same style as recommendation cards), not just genre/director tables.

## Decisions
- User picks how many to show (a number input, 5–20).
- Only fetched on a "Refresh" button click, not automatically — same pattern as "Find my next 10 movies."

## How
New function in `recommender.py` that resolves your top-N rated movies' IMDb IDs to TMDB posters/details (reuses existing `TMDBClient` methods). Rendered with the same card layout already used for recommendations.
