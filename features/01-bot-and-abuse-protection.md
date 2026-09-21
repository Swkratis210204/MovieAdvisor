# Go-live: Bot and abuse protection

## Current risk
Low. TMDB calls run on the visitor's own key, not a shared one — a bot can only burn its own quota. The only shared secret is `GROQ_API_KEY` (optional "why" rewrite), and it's only reachable after someone completes a run with their own TMDB key first. No observed abuse.

## What to do before going live
Nothing blocking. Ship without bot protection.

## Revisit if
- Groq costs actually spike (check the Groq console usage dashboard weekly for the first month).
- The app gets shared widely and real scraping/abuse shows up in logs.

## How, if needed later
Gate just the Groq "rewrite why lines" checkbox with Cloudflare Turnstile (free, doesn't track or fingerprint anyone) rather than gating the whole app. The core recommend/explore flow doesn't need protecting since it costs you nothing.
