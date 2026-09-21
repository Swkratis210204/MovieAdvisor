# Go-live: Handling traffic spikes

## What
Make sure a sudden wave of visitors (Reddit/HN front page, etc.) degrades gracefully instead of falling over or running up a bill.

## Decisions to make
- **Fly machine count/size.** Currently 1 shared-cpu-1x machine, `min_machines_running = 1`. Fly can autoscale by adding `auto_stop_machines`/`auto_start_machines` (already set) plus a higher `[http_service.concurrency]` limit, or just bump `min_machines_running` / machine size if you expect sustained load.
- **Per-visitor TMDB key means TMDB rate limits scale with users, not with you** — the real bottleneck under heavy traffic is CPU/memory on the Fly machine running many Streamlit sessions at once, not TMDB.
- **Groq key is shared** — this is the one thing that doesn't scale for free. Consider a per-session or per-IP cap on how many times the LLM rewrite can be used, or disable it under heavy load.

## Done
1. **`[http_service.concurrency]` set in `fly.toml`** — `soft_limit = 20`, `hard_limit = 25` connections. Past ~20 concurrent Streamlit sessions on the current shared-cpu-1x/1GB machine, Fly should spin up an additional machine rather than let one machine get overloaded for everyone.
2. **Alerting already covered** — see `04-monitoring-and-error-tracking.md`: UptimeRobot catches full outages, Sentry catches exceptions. No separate "response time spike" alert added on top of these; reasonable for this app's scale.

## Deliberately deferred (not done, and that's a decision, not a gap)
**Load-testing** (`locust`/`hey` against the live URL or a staging deploy) is skipped for now. There's no planned traffic event (launch post, etc.) at time of writing — running a real load test against a single always-on production machine purely for hypothetical future traffic isn't worth the risk of disrupting actual current visitors for a data point nobody currently needs.

**Revisit when:** an actual traffic event is planned (a launch post, sharing the link somewhere with real reach). At that point, load-test against a temporary staging deploy rather than the production URL, so real visitors aren't affected by the test itself — same logic as testing the UptimeRobot alert against a fake URL instead of stopping the real production machine.
