# Go-live: Privacy policy / terms of service

## What
The app processes personal data (uploaded IMDb rating history, pasted TMDB/Groq API keys) even though it's kept in-memory only and never written to disk. "We don't persist it" is a design fact buried in `DEPLOYMENT.md` — a public-facing page should say the same thing to visitors, not just to future maintainers.

## How
A single short page (or an `st.expander` in the app itself, or a separate static page) covering:
- What data is collected: uploaded ratings CSV, API keys — both kept only in the browser session's server-side memory, never written to disk or a database, never shared with other users, wiped when the session ends.
- What third parties are involved: TMDB (movie data, using the visitor's own key), optionally Groq (only if the visitor enables the LLM rewrite).
- No cookies / no tracking, if using a cookie-free analytics tool (see 04-monitoring-and-error-tracking.md) — say so explicitly, since "no cookie banner" only works if it's actually true.
- Contact info for questions or data-deletion requests (even though there's nothing to delete, given the no-persistence model).

## Note
This matters more if the audience could include EU/UK visitors (GDPR) — even a lightweight, honest privacy note reduces risk versus having nothing at all.
