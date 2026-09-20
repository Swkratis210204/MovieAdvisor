# Deployment Plan

How to take this app from "runs on my machine" to "a link anyone can open."

## What changed to make this deployable

- **No shared TMDB key required.** The sidebar now has a "Your TMDB API key" field. Each visitor pastes in their own free TMDB key, which is used only for their browser session (never written to disk, never shared with other users, never sent anywhere except TMDB). If `TMDB_API_KEY` is set in the server's environment, it's used as a fallback — handy for local single-user use, irrelevant once this is public.
- **The disk cache no longer crashes the app** if the filesystem it's running on is read-only or unwritable (`cache.py`). It silently disables itself instead. This matters because some hosts run containers with restricted filesystems.

## Steps

### 1. Dockerize — done
`Dockerfile` and `.dockerignore` are in the repo root. Build and test locally:

```
docker build -t next10movies .
docker run -p 8501:8501 next10movies
```

Open http://localhost:8501 — you should see the app with an empty "Your TMDB API key" field (no `.env` is baked into the image).

### 2. Push to GitHub
Deployment platforms deploy from a git repo. Init git here if you haven't, commit, push to a new GitHub repo. Double check `.env` is not committed (it's in `.gitignore`).

### 3. Pick a host and deploy the container
Recommended: **Fly.io** — free tier is enough for this, deploys straight from the Dockerfile, has persistent volumes and automatic HTTPS.

```
fly launch          # detects the Dockerfile, asks a few questions, creates fly.toml
fly deploy
```

Alternatives: Railway (simplest dashboard, similar flow), or a small VM (DigitalOcean/Hetzner) if you want full control and are fine running Docker + Caddy yourself.

### 4. (Optional) Attach a persistent volume for the TMDB cache
Without this, the on-disk TMDB response cache resets every time the container restarts/redeploys — the app still works, it's just slower on first use after each restart (has to refetch from TMDB). With a volume mounted at `/app/.cache`, cached responses survive restarts.

On Fly.io:
```
fly volumes create cache_data --size 1
```
then mount it at `/app/.cache` in `fly.toml`.

Skip this step entirely if you don't care about the extra speed — it's not required for correctness.

### 5. (Optional) Gate access
Since anyone with the link can now use the app (using their *own* TMDB key, not yours — see below), there's no API-cost reason to lock it down. Add basic auth only if you want to control who sees it at all, e.g. a Caddy reverse proxy with `basicauth` in a few lines of config.

### 6. Server secrets
No server-side TMDB secret is required anymore for public use — each user supplies their own key at runtime. If you still want a fallback default key for convenience (e.g. for yourself), set `TMDB_API_KEY` as an environment variable/secret in the host's dashboard (`fly secrets set TMDB_API_KEY=...`), never in the Docker image itself.

## What you don't need

- **No database.** Nothing persists server-side across sessions — each visitor's uploaded ratings CSV lives only in their own browser session's memory.
- **No Redis.** The TMDB cache holds no per-user data (just public movie metadata), so it's safe to share across all users on a single instance. Redis would only matter if you scaled to multiple app instances that needed to share that cache — not needed for this app's expected traffic.
- **No load balancer / multiple replicas.** Streamlit keeps a live WebSocket connection per session; running more than one instance behind a load balancer needs sticky sessions to work correctly. One instance is enough for personal or small-group use.

## Checklist

- [ ] Dockerfile builds and runs locally (`docker build` / `docker run`)
- [ ] Repo pushed to GitHub, `.env` confirmed not committed
- [ ] Deployed to a host (Fly.io/Railway/VM) from the Dockerfile
- [ ] App reachable over HTTPS at a public URL
- [ ] Sidebar "Your TMDB API key" field works end-to-end with a real key
- [ ] (Optional) Persistent volume mounted for `/app/.cache`
- [ ] (Optional) Basic auth added if you want to restrict who can open the link
