# Feature: Bot protection (not user authentication)

## Goal, precisely
Stop automated/scripted traffic from hammering the app — not identify, remember, or track individual humans. No accounts, no email, no per-person identity. A person should be able to use the app anonymously; a bot/script shouldn't be able to use it at all (or should be sharply rate-limited).

This replaces the earlier draft of this file, which was framed around "who is this person" (invite codes, email magic-links, OAuth). That's the wrong problem — none of those are needed here, and OAuth/email would actively work against the "don't track anyone" goal by introducing real identity into the app.

## Why this matters for this app specifically
Every "Find my next 10 movies" click burns TMDB requests (and optionally Groq requests, if the LLM rewrite is on). A script hammering the button in a loop could burn through rate limits fast, degrading the experience for real visitors — this is the actual risk, not "a stranger might see the app."

## Options, cheapest to most robust

### A. Cloudflare Turnstile (recommended)
A free, privacy-preserving "prove you're not a bot" widget — Cloudflare's explicit pitch is that it does *not* fingerprint or track users the way reCAPTCHA does, which matches the goal here exactly.
- **How it'd work:** embed the Turnstile widget via `st.components.v1.html(...)` before the "Find my next 10 movies" button becomes usable. On submit, the widget produces a token; the app makes one server-side call to Cloudflare's `siteverify` endpoint (via `requests`, same pattern as everything else in `tmdb_client.py`) to confirm the token is valid before running the pipeline.
- **Needs:** a free Cloudflare account + site key/secret key pair (env vars, same pattern as `TMDB_API_KEY`).
- **Effort:** small-medium — no new architecture, just one widget + one verification call gating the existing button.

### B. Simple rate limiting per session
Cap how many times a single browser session can trigger the recommendation pipeline in a given window (e.g. 5 runs per 10 minutes), tracked in `st.session_state` with timestamps.
- **Upside:** zero external dependencies, a few lines of code.
- **Limitation:** only limits *one session* — a script opening many fresh sessions isn't slowed down at all. Best paired with A, not used alone.

### C. Lightweight challenge (no third party)
A trivial "what is 4 + 7?" style check rendered as plain text before the button unlocks.
- **Upside:** zero dependencies, zero signup, no external service.
- **Limitation:** trivially defeated by any bot that actually parses the page — only stops the laziest scripts, not a real deterrent.

## Recommendation
**A (Turnstile) + B (session rate limit) together** — Turnstile stops scripted abuse without identifying anyone, and the session-level rate limit is a free extra layer that costs almost nothing to add alongside it. Skip C; it's not worth building since it barely raises the bar.

## Effort estimate
Small-medium for A, small for B. Both are additive to the existing "Find my next 10 movies" button — no restructuring of the app needed.

## Decisions
- **Only the main "Find my next 10 movies" pipeline is gated by Turnstile**, not the Groq-backed "why" rewrite checkbox — that's where the real API cost/abuse risk actually is (dozens of TMDB calls per click), and it only runs at all if someone's already past the Turnstile gate to get results in the first place.
- **Ship Turnstile (A) first; add the session rate limit (B) only if abuse is actually observed** — no need to tune a rate-limit window speculatively before there's a real signal it's needed.
