# Go-live: Tracking, monitoring, and error alerting

These are three different concerns, easy to conflate — do all three:

## 1. Uptime monitoring — ✅ done
UptimeRobot is set up, monitoring `https://personalmovie.fly.dev/` every 5 minutes with an email alert contact attached. The alert path was verified by temporarily pointing the monitor at a broken URL, confirming it flipped to "Down" and sent the email, then pointing it back at the real URL — without ever touching the live production machine (stopping the actual Fly machine turned out not to work as a test, since `auto_start_machines = true` wakes it back up on the very next incoming request, including a monitor's own check).

## 2. Error tracking
Different from uptime — this is "the app is up but throwing exceptions." Add Sentry's Python SDK (`sentry_sdk.init(...)` near the top of `app.py`) so unhandled exceptions in a user's session get reported instead of silently failing in their browser.

## 3. Usage analytics
Privacy-friendly, cookie-free options fit this app well since it already avoids tracking users: Plausible or Umami (self-hostable or hosted, both GDPR-friendly, no cookie banner needed). Skip Google Analytics unless you specifically want it — it needs a cookie consent banner in the EU/UK.

## 4. Cost/usage alerts
- Fly.io: set a billing alert in the Fly dashboard.
- Groq: check the usage dashboard regularly since `GROQ_API_KEY` is shared across all visitors (see 01-bot-and-abuse-protection.md).
- TMDB: no cost risk — each visitor uses their own free key.
