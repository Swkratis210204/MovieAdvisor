# Feature: Better authentication

## Current state
`APP_PASSWORD` (see `app.py`, `DEPLOYMENT.md`) is a single shared password gate: one secret, no identity, no per-user anything. It's currently unset (app is fully open).

## Why this might be worth doing
A shared password works but doesn't scale past "a few people I text the password to" — everyone looks identical to the app, there's no way to revoke one person's access without changing the password for everyone, and there's no way to remember anything per-person (e.g. their last uploaded CSV, their filter preferences).

## Options, roughly cheapest to most involved

### A. Per-user invite codes (small step up from today)
Instead of one shared `APP_PASSWORD`, keep a small list of valid codes (env var, comma-separated, or a tiny JSON file). Each person gets their own code; revoking one doesn't affect others.
- **Effort:** small — a few lines in the existing password-gate block in `app.py`.
- **Limitation:** still just a shared secret per person, not real identity (no email, no persistent account).

### B. Email magic-link (passwordless)
User enters their email → app emails a one-time signed link → clicking it logs them in for that session. No database needed: use a signed, time-limited token (e.g. Python's `itsdangerous.URLSafeTimedSerializer`) embedding the email, verified on click without persisting anything server-side.
- **Needs:** an email-sending service (Resend or SendGrid both have free tiers), a `SECRET_KEY` env var for signing tokens, and a way for the Streamlit app to read a token from the URL query params on load.
- **Effort:** medium — new module for token generation/verification, integration with an email API, URL-param handling in `app.py`.
- **Upside:** real per-user identity (an email address) without running a database, which opens the door to feature 02 (remembering someone's profile) later.

### C. OAuth (Google/GitHub sign-in)
Real third-party identity, no passwords or emails to manage at all.
- **Needs:** registering an OAuth app with the provider, handling the redirect/callback flow. Streamlit's native auth support (`st.login`, `st.experimental_user`) may cover this in newer versions — worth checking against the installed Streamlit version before building anything custom.
- **Effort:** medium-large — most complex of the three, but the most "real" auth experience and the least code we have to trust ourselves (Google/GitHub handle the actual credential security).

## Recommendation
Start with **A** if the only goal is "let a few specific people in, and let me revoke one without bugging everyone else." Only move to **B** or **C** if a real reason shows up to know *who* is using the app (e.g. wanting to remember someone's profile between visits — see feature 02).

## Open questions
- Do we actually want to remember anything per-user, or is access control the whole goal? If it's just access control, invite codes (A) are enough and B/C are overkill.
- If email (B), what does "forgot to click the link" recovery look like?
