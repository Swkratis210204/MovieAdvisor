# Go-live: Tracking, monitoring, and error alerting

These are three different concerns, easy to conflate — do all three:

## 1. Uptime monitoring — ✅ done
UptimeRobot is set up, monitoring `https://personalmovie.fly.dev/` every 5 minutes with an email alert contact attached. The alert path was verified by temporarily pointing the monitor at a broken URL, confirming it flipped to "Down" and sent the email, then pointing it back at the real URL — without ever touching the live production machine (stopping the actual Fly machine turned out not to work as a test, since `auto_start_machines = true` wakes it back up on the very next incoming request, including a monitor's own check).

## 2. Error tracking — ✅ done
Sentry's Python SDK is wired in (`sentry_sdk.init(...)` near the top of `app.py`), configured for error monitoring only — no tracing/profiling/logs, and `send_default_pii=False` so it doesn't capture visitor IPs/headers (stays consistent with the app's own "no visitor tracking" privacy note). DSN lives in the `SENTRY_DSN` Fly secret, unset locally by default (no-ops safely without it). Verified working end-to-end: a manual test event (`sentry_sdk.capture_message(...)`) sent with the production DSN showed up in the Sentry dashboard's Feed within a minute.

## 3. Usage analytics
Privacy-friendly, cookie-free options fit this app well since it already avoids tracking users: Plausible or Umami (self-hostable or hosted, both GDPR-friendly, no cookie banner needed). Skip Google Analytics unless you specifically want it — it needs a cookie consent banner in the EU/UK.

## 4. Cost/usage alerts
- Fly.io: set a billing alert in the Fly dashboard.
- Groq: check the usage dashboard regularly since `GROQ_API_KEY` is shared across all visitors (see 01-bot-and-abuse-protection.md).
- TMDB: no cost risk — each visitor uses their own free key.
