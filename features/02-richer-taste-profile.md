# Feature: Drill-down on profile stats

## What
Every aggregate stat becomes clickable to show the actual movies behind it:
- Click a director/genre in the top-genres/top-directors table → see which of your movies those are.
- Click a bar in the rating distribution (e.g. "rated 4: 5 movies") → see which 5 movies.

## How
No TMDB calls needed — this is all already in the uploaded CSV. Use `st.expander` or `st.dataframe` selection under each table/chart, filtering `df` by that genre/director/rating and listing title + year + your rating.
