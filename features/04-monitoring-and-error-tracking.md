# Go-live: Tracking, monitoring, and error alerting

These are three different concerns, easy to conflate — do all three:

## 1. Uptime monitoring — ✅ done
UptimeRobot is set up, monitoring `https://personalmovie.fly.dev/` every 5 minutes with an email alert contact attached. The alert path was verified by temporarily pointing the monitor at a broken URL, confirming it flipped to "Down" and sent the email, then pointing it back at the real URL — without ever touching the live production machine (stopping the actual Fly machine turned out not to work as a test, since `auto_start_machines = true` wakes it back up on the very next incoming request, including a monitor's own check).

## 2. Error tracking — ✅ done
Sentry's Python SDK is wired in (`sentry_sdk.init(...)` near the top of `app.py`), configured for error monitoring only — no tracing/profiling/logs, and `send_default_pii=False` so it doesn't capture visitor IPs/headers (stays consistent with the app's own "no visitor tracking" privacy note). DSN lives in the `SENTRY_DSN` Fly secret, unset locally by default (no-ops safely without it). Verified working end-to-end: a manual test event (`sentry_sdk.capture_message(...)`) sent with the production DSN showed up in the Sentry dashboard's Feed within a minute.

## 3. Usage analytics — ✅ done
Umami Cloud is wired in via a small inline script injected through `st.components.v1.html` (`app.py`) — `st.markdown` strips `<script>` tags, so that's the only way to get a real script tag onto the page. Gated behind `st.session_state` so it fires once per real visit, not once per Streamlit rerun (every widget interaction reruns the whole script, which would otherwise inflate the pageview count on every click/filter change). The website ID lives in `fly.toml`'s plain `[env]` block, not a secret — it's visible in the page source to any visitor anyway, so there's nothing to protect. Deliberately unset in local `.env` so local dev runs don't pollute real visit stats. Cookie-free, GDPR-friendly, no consent banner needed.

## 4. Cost/usage alerts — ✅ done
- Fly.io: billing/spending alert set in the Fly dashboard.
- Groq: hard daily call cap in code — see `08-secrets-and-cost-controls.md` (no billing risk either way, since there's no payment method on the Groq account).
- TMDB: no cost risk — each visitor uses their own free key.

All four sub-items closed.
