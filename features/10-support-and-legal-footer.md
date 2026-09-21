# Go-live: Support contact and footer

## What
No way for a visitor to report a bug, ask a question, or flag misuse. No footer at all currently.

## How
Add a simple footer (`st.caption`/`st.markdown` at the bottom of `app.py`, shown on every tab) with:
- A contact method: an email address, or a link to this repo's GitHub Issues page.
- The TMDB attribution line (see 06-tmdb-attribution.md) — this is the natural place to put it.
- A link to the privacy note (see 07-privacy-policy-and-tos.md), if that's a separate page rather than inline.

Keep it to a couple of lines — this is a small personal tool, not a company site.
