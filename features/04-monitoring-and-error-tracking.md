# Go-live: Tracking, monitoring, and error alerting

These are three different concerns, easy to conflate — do all three:

## 1. Uptime monitoring
Something external that pings the app and tells you when it's down. UptimeRobot or Better Uptime (both have free tiers) hitting `https://yourdomain.com/` every few minutes is enough.

## 2. Error tracking
Different from uptime — this is "the app is up but throwing exceptions." Add Sentry's Python SDK (`sentry_sdk.init(...)` near the top of `app.py`) so unhandled exceptions in a user's session get reported instead of silently failing in their browser.

## 3. Usage analytics
Privacy-friendly, cookie-free options fit this app well since it already avoids tracking users: Plausible or Umami (self-hostable or hosted, both GDPR-friendly, no cookie banner needed). Skip Google Analytics unless you specifically want it — it needs a cookie consent banner in the EU/UK.

## 4. Cost/usage alerts
- Fly.io: set a billing alert in the Fly dashboard.
- Groq: check the usage dashboard regularly since `GROQ_API_KEY` is shared across all visitors (see 01-bot-and-abuse-protection.md).
- TMDB: no cost risk — each visitor uses their own free key.
