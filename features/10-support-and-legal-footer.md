# Go-live: Support contact and footer

## What
No way for a visitor to report a bug, ask a question, or flag misuse. No footer at all currently.

## Done
Footer added at the bottom of `app.py` (outside the tabs, so it shows everywhere) with:
- A contact method: link to this repo's GitHub Issues page.
- The TMDB attribution line (see 06-tmdb-attribution.md).
- A "Privacy & data handling" expander (see 07-privacy-policy-and-tos.md).
- A one-line **as-is/no-warranty disclaimer**: "This is a personal, hobby project provided as-is, with no warranty of any kind. Use at your own risk." Cheap insurance against liability now that this is a real public tool, not a blocker to shipping but worth having.
