# Go-live: CI gate and rollback plan

## What
`fly deploy` currently ships whatever's in the local working tree straight to production, with no automated check in between. One bad commit and a broken build is live.

## Done
`.github/workflows/fly-deploy.yml` already auto-deployed on every push to `main`/`master` via `flyctl deploy`, with no test gate. It now has two jobs:
1. **`test`** — checks out the repo, installs `requirements.txt`, runs `pytest`.
2. **`deploy`** — `needs: test`, so it only runs (and only then pushes to Fly) if the test job succeeded. A failing test blocks the deploy entirely — GitHub Actions skips the deploy job rather than running it against broken code.

This means pushing to `main` with a failing test no longer reaches production at all — you'll see a red X on the push in GitHub instead of a broken app going live. Manually running `fly deploy` from a laptop still bypasses this (it's a local command, not routed through CI), so prefer pushing to `main` and letting the workflow deploy over running `fly deploy` by hand from now on.

## Confirmed working
Pushed a commit with this workflow to `main` — the `test` job ran and passed, the `deploy` job then ran automatically (`needs: test`), and Fly release `v28` came out `complete`, serving `200`. The `FLY_API_TOKEN` secret was already set in the repo. The gate works end to end, not just in theory.

## Still to do
Know the rollback command before you need it: `fly releases` lists past deploys, `fly deploy --image <previous-image-ref>` (or `fly apps releases rollback` depending on CLI version) reverts to a known-good one. Test this once on a non-critical change so it's not the first time you're doing it during an actual incident.
