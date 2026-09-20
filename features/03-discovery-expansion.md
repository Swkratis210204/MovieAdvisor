# Feature: Discovery / expand-the-search mode

## Current state
The entire recommendation pipeline (`recommender.py`) is anchored to your own ratings: every candidate has to trace back to "similar to one of your favorites." There's no way to see movies that *aren't* connected to your history at all — no trending, no "popular right now," no deliberate genre exploration outside what you've already rated highly.

## What this feature adds
A second mode/tab — "Explore" alongside the existing "Recommended for you" — that surfaces movies through different lenses, not required to trace back to your CSV at all:

- **Trending now / popular this week** — straight from TMDB's `/trending/movie/week` or `/discover/movie` sorted by popularity, no personalization at all. Good for "what's everyone else watching."
- **Genres you rarely rate** — the inverse of your top-genre list: pick genres you have few or no ratings in, and surface well-reviewed movies from those genres. Uses the taste profile that already exists (`taste_profile.py`) — just reads it in reverse (lowest-count/lowest-affinity genres instead of highest).
- **Opposite-of-you picks** — movies with strong ratings but in genres/directors you've historically rated *below* your average, framed as "might surprise you." A slightly more editorialized version of the above.
- **A "how adventurous" slider** — a blend control between "close to your taste" (today's existing pipeline) and "totally unconnected to your history" (trending/discover), so the same UI serves both a comfort-pick and a discovery-pick without two totally separate screens.

## Why this might be worth doing
The current app only ever answers "more of what I already like." That's the right default, but it means someone who's rated mostly action movies will never see a great documentary suggested, even if they might enjoy one — because nothing in their history points to it. A pure discovery mode fixes the "filter bubble" problem the personalized pipeline inherently has.

## Implementation approach
- New functions in `recommender.py` (or a new `discovery.py` module, to keep the personalized pipeline's code separate from this): `get_trending(client)`, `get_genre_gap_picks(profile, client)`. These are much simpler than the main pipeline — mostly a direct TMDB `/discover` or `/trending` call, filtered by the existing `MIN_VOTES` threshold, no seed/aggregation/scoring machinery needed.
- Reuse the same card-rendering code in `app.py` — these are still `Candidate`-shaped objects, just built differently (skip `frequency_score`/`recommended_by`, since there's no "recommended by your favorites" reason for a pure discovery pick — the "why" text would instead be something like "Trending this week" or "You rarely rate Documentary — this one's highly reviewed").
- Add a tab or toggle in `app.py` (`st.tabs(["Recommended for you", "Explore"])`) so this is clearly a different mode, not mixed into the personalized top 10.

## Effort estimate
Medium. The TMDB calls themselves are simple (arguably simpler than the existing pipeline), but it's a genuinely new section of the app (new tab, new card "why" text, a few new small functions) rather than an extension of existing code paths.

## Open questions
- Should discovery picks still exclude movies you've already rated? (Probably yes, same as today.)
- Is "opposite of you" actually wanted, or does it just produce noise? Worth trying trending + genre-gap first, since those are more obviously useful, before building the more editorial "opposite" framing.
