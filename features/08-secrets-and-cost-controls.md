# Go-live: Secrets management and cost controls

## What
`APP_PASSWORD`, `TMDB_API_KEY` (optional server fallback), and `GROQ_API_KEY` are set as Fly secrets (`fly secrets set ...`), never committed. Before going live, make sure that discipline holds and that a leaked key has a clear recovery path.

## Done
- **No leak found.** Scanned the entire git history (`git log --all -p`) for `.env` commits and for common key-format patterns (Groq `gsk_...`, OpenAI-style `sk-...`, Google `AIza...`, TMDB-style hex keys) — nothing. `.env` has never been committed.
- **Hard daily quota cap on the shared Groq key** (`llm_rewrite.py`): every call increments a UTC-day counter in the existing on-disk cache; once `GROQ_DAILY_CALL_LIMIT` (default 300, override via env var) is hit, `rewrite_why()` stops calling Groq entirely and silently falls back to the plain deterministic why-text until the day rolls over. The sidebar checkbox disables itself and shows "today's shared rewrite quota is used up" once the cap is reached, and always shows a `used/limit` caption.
- **No billing risk.** No payment method is on file with Groq — this is the plain free tier, so there's no bill to protect against. The daily cap above exists to protect the *shared free quota* from one burst exhausting it for every visitor for the rest of the day, not to protect against a charge. No Groq console billing alert needed as a result — nothing to alert on.

## Still to do
Know how to rotate each secret fast (this is a runbook, not code — write it down somewhere you'll find it during an incident):
- Groq: revoke + regenerate in the Groq console, `fly secrets set GROQ_API_KEY=...`.
- TMDB (server fallback key, if set): same pattern via TMDB account settings.
- `APP_PASSWORD`: just `fly secrets set APP_PASSWORD=...` with a new value.
