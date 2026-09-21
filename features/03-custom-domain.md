# Go-live: Custom domain

## What
Move off `personalmovie.fly.dev` onto your own domain.

## How
1. Buy a domain (Namecheap, Cloudflare Registrar, etc.) if you don't have one.
2. `fly certs create yourdomain.com` (and `www.yourdomain.com` if you want both).
3. Add the DNS records Fly gives you (an `A`/`AAAA` pair or `CNAME`, depending on apex vs subdomain) at your registrar/DNS host.
4. Wait for `fly certs show yourdomain.com` to report the cert as issued (usually minutes).
5. Update any hardcoded links (README, this repo's description, social previews) to the new domain.

## Note
If you put Cloudflare in front of the domain for DNS, keep Cloudflare's proxy (orange cloud) off for the Fly hostname unless you specifically want Cloudflare's CDN/WAF in front — it can complicate Fly's own TLS handshake if misconfigured.
