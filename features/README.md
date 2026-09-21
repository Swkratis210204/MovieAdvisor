# Go-live checklist

What's left before this stops being "runs on my machine" and becomes a real public webapp. Ordered roughly by how much it matters.

**Do first (compliance/legal risk):**
1. ✅ [06-tmdb-attribution.md](06-tmdb-attribution.md) — TMDB requires attribution wherever their data is shown; not optional. Done: added to the app footer and main README.
2. ✅ [07-privacy-policy-and-tos.md](07-privacy-policy-and-tos.md) — say publicly what's already true in code: nothing persists server-side. Done: added as a "Privacy & data handling" expander in the app footer.

**Do before real traffic:**
3. ✅ [08-secrets-and-cost-controls.md](08-secrets-and-cost-controls.md) — rotation plan + cap the shared Groq quota. Done: no git-history leak found, a hard daily call cap protects the shared free quota in code, and no billing risk exists (no payment method on file with Groq). Rotation commands are written down in the file for if a key ever needs replacing.
4. 🟡 [09-ci-and-rollback.md](09-ci-and-rollback.md) — tests-gate deploys, know how to roll back. Mostly done: the GitHub Actions workflow now runs `pytest` and only deploys to Fly if it passes. Still to do: confirm the `FLY_API_TOKEN` secret is set in GitHub, and actually run the rollback command once so it's not new during a real incident.
5. [04-monitoring-and-error-tracking.md](04-monitoring-and-error-tracking.md) — uptime checks, error tracking, usage analytics, cost alerts
6. [02-traffic-and-scaling.md](02-traffic-and-scaling.md) — what happens if a launch post spikes traffic

**Nice to have / lower priority:**
7. [03-custom-domain.md](03-custom-domain.md) — off `*.fly.dev` onto your own domain
8. [10-support-and-legal-footer.md](10-support-and-legal-footer.md) — contact link + footer
9. [05-seo.md](05-seo.md) — meta tags, social previews; low ROI for a single-page tool
10. [01-bot-and-abuse-protection.md](01-bot-and-abuse-protection.md) — low risk today, revisit only if abuse actually shows up
