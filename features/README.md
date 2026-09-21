# Go-live checklist

What it takes to go from "runs on my machine" to a real public webapp.

## Mandatory to ship — not done yet

Everything else on this page is either done or a deliberate, reasoned skip. These two are the only genuine blockers left:

1. ⬜ **A custom domain.** [03-custom-domain.md](03-custom-domain.md) — `*.fly.dev` works, but a real domain is table stakes for something you're actually shipping.
2. ⬜ **WHOIS privacy protection**, enabled the moment the domain is bought. Most registrars expose the buyer's name/home address publicly unless this is turned on (sometimes free, sometimes a couple dollars/year) — easy to forget, and it matters the instant the domain is public. Not its own file since it's a one-checkbox step during domain purchase, not a build task.

Nothing else is a hard requirement — no missing legal step, no missing technical safeguard. The rest of this list is either already closed or intentionally deferred.

## Already done ✅

**Compliance/legal:**
1. [06-tmdb-attribution.md](06-tmdb-attribution.md) — TMDB requires attribution wherever their data is shown. Added to the app footer and main README.
2. [07-privacy-policy-and-tos.md](07-privacy-policy-and-tos.md) — say publicly what's already true in code: nothing persists server-side. Added as a "Privacy & data handling" expander in the app footer, alongside a one-line as-is/no-warranty disclaimer (see #6).

**Reliability/cost:**
3. [08-secrets-and-cost-controls.md](08-secrets-and-cost-controls.md) — no git-history leak found; a hard daily call cap protects the shared Groq quota in code; no billing risk exists (no payment method on file with Groq). Rotation commands are written down for if a key ever needs replacing.
4. [09-ci-and-rollback.md](09-ci-and-rollback.md) — the GitHub Actions workflow runs `pytest` and only deploys to Fly if it passes, proven live across several real deploys. Rollback command is written down for if it's ever needed for real.
5. [04-monitoring-and-error-tracking.md](04-monitoring-and-error-tracking.md) — UptimeRobot (verified alert), Sentry (verified live event), Umami analytics (live), Groq daily cap, and a Fly.io billing/spending alert are all set.
5b. [02-traffic-and-scaling.md](02-traffic-and-scaling.md) — `fly.toml` has connection concurrency limits so Fly scales out past ~20 concurrent sessions instead of overloading one machine. Alerting already covered by #5.

**Support/UX:**
6. [10-support-and-legal-footer.md](10-support-and-legal-footer.md) — footer has a GitHub issues link, TMDB attribution, a privacy expander, and the no-warranty disclaimer.

## Deliberately deferred (a decision, not a gap)

7. [05-seo.md](05-seo.md) — meta tags, social previews. Low ROI for a single-page tool whose traffic will come from shares, not search.
8. [01-bot-and-abuse-protection.md](01-bot-and-abuse-protection.md) — low risk today (no shared-cost API surface to protect), revisit only if real abuse shows up.
9. Load-testing (part of #5b) — deferred until an actual traffic event is planned, so a live single-machine production app isn't disrupted testing for a spike that isn't scheduled yet.

Important but not mandatory, worth doing eventually and named explicitly so it isn't mistaken for a requirement: a fuller Terms of Service beyond the one-line disclaimer already in place, if this ever takes on real users at scale.
