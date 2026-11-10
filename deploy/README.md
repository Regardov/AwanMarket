# Production deployment

1. Point the domain's A/AAAA record to the server.
2. Copy `.env.example` to `.env`, replace every secret and set `DOMAIN`.
3. Keep PostgreSQL private; only ports 80/443 should be public.
4. Run `docker compose -f docker-compose.yml -f compose.production.yml up -d --build`.
5. Verify `https://YOUR_DOMAIN/health` and sign in with the configured admin account.

Caddy provisions and renews TLS automatically. Back up the `postgres_data` volume and rotate
`SECRET_KEY` only when forcing all sessions to expire.

