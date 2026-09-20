# Next 10 Movies

A local Streamlit app that reads your IMDb ratings export and recommends the next 10 movies you should watch, using TMDB's recommendation/similar endpoints combined with a taste profile built from your own ratings.

## Setup

1. Create a virtual environment and install dependencies:

   ```
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Get a free TMDB API key at https://www.themoviedb.org/settings/api, then create a `.env` file (copy `.env.example`):

   ```
   TMDB_API_KEY=your_tmdb_api_key_here
   ```

## Run the app

```
streamlit run app.py
```

Then open the URL Streamlit prints (usually http://localhost:8501), upload your IMDb `ratings.csv` export (from IMDb: **Your Ratings → ⋯ menu → Export**), and click **Find my next 10 movies**.

There's also a "use bundled sample_ratings.csv" checkbox for a quick demo without your own export.

## How it works

```mermaid
flowchart TD
    A["You upload your ratings.csv"] --> B["Clean the data\nkeep movies only, fix\nmissing/odd values"]

    B --> C["Build your taste profile\navg rating per genre & per director,\nweighted down if you've only\nseen 1-2 of them"]

    B --> D["Pick your favorites as seeds\nrating >= 8, or top 40\nif you have a lot"]
    D --> E["Ask TMDB: 'people who liked\nthis also liked...' for\nevery favorite"]
    E --> F["Tally the suggestions\nsame movie suggested by\nmultiple favorites -> counts more,\nweighted by how much you\nloved that favorite"]

    F --> G["Pull full details for the\ntop-tallied candidates\ngenres, director, runtime, votes"]
    G --> H["Drop anything you've already\nrated, or with too few votes\nto trust"]

    C --> J
    H --> I["Apply your sidebar filters\nruntime, year, genre in/out"]
    I --> J["Score each candidate\ntally weight + genre affinity\n+ director affinity + TMDB quality"]
    J --> K["Diversify the list\ncap at 3 picks per\ndirector or franchise"]
    K --> L["Show your next 10\n(+ 'load 10 more' from\nthe same scored pool)"]
```

1. **Clean the data** — keeps only real movies from your upload, ignoring TV shows and episodes, and handles missing/odd values gracefully.
2. **Build your taste profile** — your average rating, plus a per-genre and per-director average, pulled toward the overall average when you've only rated one or two of them (so a single 10/10 from an unknown director doesn't skew everything).
3. **Pick seeds** — your highest-rated movies (rating ≥ 8, capped at your top 40) become the starting points for discovery.
4. **Ask TMDB for similar movies** — for each seed, ask what viewers who liked it also liked/were recommended.
5. **Tally the suggestions** — every time a movie is suggested by one of your seeds, it earns weight proportional to how much you loved that seed (rating − your average). A movie suggested by five favorites you rated 9-10 outweighs one suggested once by a movie you rated 8.
6. **Enrich the top candidates** — pull real details (director, genres, runtime, vote count) only for the highest-tallied candidates, to keep API usage reasonable.
7. **Drop what doesn't belong** — anything already in your ratings, or with too few TMDB votes to be a trustworthy candidate.
8. **Filter, then score** — your sidebar filters (runtime/year/genre) are applied first; remaining candidates are scored by combining the tally weight, genre affinity, director affinity, and a small overall-quality boost from TMDB's rating.
9. **Diversify** — the ranked list is walked top-down, skipping anything that would push a single director or franchise past 3 picks, so the final list isn't just five Nolan movies.
10. **Show results** — top 10 appear as cards (poster, why-explanation, IMDb link); "Show me 10 more" reveals the next batch from the same scored pool instantly, no extra lookups needed.

Movie data is cached on disk so re-running with the same filters is fast and doesn't repeat lookups unnecessarily.

### Optional: natural-language "why" text

The "why" explanation for each recommendation is generated directly from your data by default (e.g. *"Recommended by 4 of your favorites; matches your love of sci-fi and Nolan."*) — no AI involved. If you want it rephrased in more natural prose, there's an opt-in sidebar checkbox that uses an open-weight model (currently `openai/gpt-oss-20b`) hosted free by [Groq](https://console.groq.com) to rewrite it. This requires a free `GROQ_API_KEY` in `.env` and is off by default; the app works fully without it.

## Tests

```
pytest
```

Tests cover CSV parsing/validation (`tests/test_imdb_parser.py`), taste-profile affinity scoring (`tests/test_profile.py`), and candidate scoring/filtering/diversity logic (`tests/test_recommender.py`), using `sample_ratings.csv` as fixture data.

