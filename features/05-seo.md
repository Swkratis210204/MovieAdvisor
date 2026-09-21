# Go-live: SEO and discoverability

## What
Right now the app is a bare Streamlit page — no custom title tag, meta description, social preview image, sitemap, or robots.txt. `st.set_page_config(page_title=...)` sets the browser tab title but not much else search engines or link previews care about.

## How
Streamlit doesn't give raw control over `<head>` tags out of the box. Options, in order of effort:
1. **Cheap win:** `st.set_page_config` already sets `page_title` and `page_icon` — make sure both are set well (they are: "Next 10 Movies" / 🎬).
2. **Meta description + social preview (OpenGraph/Twitter cards):** inject via `st.markdown("<meta ...>", unsafe_allow_html=True)` in the head, or a small custom `index.html` override if you want more control — fiddly with Streamlit's architecture since it doesn't expose the page shell directly.
3. **`robots.txt` / `sitemap.xml`:** a single-page app like this doesn't need much of a sitemap; a simple `robots.txt` allowing crawling is enough. Can be served via a static file if you front the app with a reverse proxy, or skipped since one page doesn't benefit much from a sitemap.
4. **Realistic expectation:** a single-page interactive tool like this won't rank well on organic search regardless of on-page SEO — most traffic will come from shares/links, not search. Don't over-invest here relative to the app's actual audience.
