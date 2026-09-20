# Feature: Bot protection

## Verdict: not worth building

TMDB calls run on the visitor's own key, not ours — a bot can only burn its own quota, not ours. Only `GROQ_API_KEY` (optional "why" rewrite) is a shared secret, and it's only reachable after someone already completed a run with their own TMDB key. No observed abuse, low realistic risk.

Revisit only if Groq costs actually spike, or the app gets shared widely and real abuse shows up. If so: gate just the Groq checkbox with Cloudflare Turnstile (free, doesn't track/identify anyone).
