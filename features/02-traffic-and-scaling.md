# Go-live: Handling traffic spikes

## What
Make sure a sudden wave of visitors (Reddit/HN front page, etc.) degrades gracefully instead of falling over or running up a bill.

## Decisions to make
- **Fly machine count/size.** Currently 1 shared-cpu-1x machine, `min_machines_running = 1`. Fly can autoscale by adding `auto_stop_machines`/`auto_start_machines` (already set) plus a higher `[http_service.concurrency]` limit, or just bump `min_machines_running` / machine size if you expect sustained load.
- **Per-visitor TMDB key means TMDB rate limits scale with users, not with you** — the real bottleneck under heavy traffic is CPU/memory on the Fly machine running many Streamlit sessions at once, not TMDB.
- **Groq key is shared** — this is the one thing that doesn't scale for free. Consider a per-session or per-IP cap on how many times the LLM rewrite can be used, or disable it under heavy load.

## How
1. Set `[http_service.concurrency]` in `fly.toml` (soft/hard limits) so Fly queues or spins up a second machine instead of one machine falling over.
2. Add a Fly alert or a simple external uptime check (see 04-monitoring-and-error-tracking.md) that pages you if response times spike.
3. Load-test locally with something like `locust` or `hey` against a staging deploy before a planned traffic event (e.g. a launch post) to see where it actually breaks.
