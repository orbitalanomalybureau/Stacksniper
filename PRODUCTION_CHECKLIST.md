# Production Launch Checklist

## Pre-Deploy

- [ ] All environment variables set in Render dashboard
- [ ] `SECRET_KEY` auto-generated (via render.yaml)
- [ ] `DATABASE_URL` uses `postgresql+asyncpg://` prefix
- [ ] `STRIPE_SECRET_KEY` set (live key, not test)
- [ ] `STRIPE_WEBHOOK_SECRET` set for production endpoint
- [ ] `SPORTSDATA_API_KEY` set
- [ ] `CORS_ORIGINS` locked to production domain only
- [ ] Debug/dev mode disabled

## Database

- [ ] Alembic migrations run successfully (`alembic upgrade head`)
- [ ] Database backups configured
- [ ] Connection pooling configured for production load

## Security

- [ ] Rate limiting active (10/min free, 60/min pro, 200/min elite)
- [ ] Security headers present (X-Content-Type-Options, X-Frame-Options, HSTS, etc.)
- [ ] X-Request-ID tracking enabled
- [ ] JWT tokens expire appropriately
- [ ] CORS restricted to production domain

## Stripe

- [ ] Webhook endpoint registered: `https://your-domain.com/api/billing/webhook`
- [ ] Webhook signing secret matches `STRIPE_WEBHOOK_SECRET`
- [ ] Test payment flow works (checkout -> subscription -> tier upgrade)
- [ ] Subscription cancellation downgrades tier to free

## Verification

- [ ] Health endpoint returns 200 with `db_connected: true`
- [ ] User registration flow works end-to-end
- [ ] Login returns valid JWT
- [ ] Projections page loads data
- [ ] Simulation can be started and returns results
- [ ] Lineup optimizer generates valid lineups

## Frontend

- [ ] Mobile layout renders correctly
- [ ] Favicon and meta tags present
- [ ] Disclaimer visible on relevant pages
- [ ] Error boundary catches React errors
- [ ] API error toasts display correctly
- [ ] All navigation links work (HashRouter)

## Monitoring

- [ ] Structured JSON logging active
- [ ] Health endpoint monitored (uptime check)
- [ ] Error rates tracked
- [ ] Render auto-deploy from `main` branch configured

## Post-Launch

- [ ] Analytics integration (optional)
- [ ] Custom domain configured with SSL
- [ ] DNS records updated (A/CNAME to Render)
- [ ] Email notifications for deploy failures
- [ ] Review Render usage/billing
