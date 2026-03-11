# Stack Sniper DFS

NFL Daily Fantasy Sports projections and Monte Carlo simulation platform. Optimize lineups with data-driven projections, run thousands of simulations, and generate contest-ready rosters.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, async SQLAlchemy, Celery |
| Frontend | React 18, Tailwind CSS, esbuild |
| Database | PostgreSQL 16 |
| Cache/Queue | Redis 7 |
| Billing | Stripe Subscriptions |
| Data | SportsData.io API |
| Deploy | Render (Blueprint) |
| CI/CD | GitHub Actions |

## Architecture

```
                    ┌──────────────┐
                    │  React SPA   │
                    │  (Static)    │
                    └──────┬───────┘
                           │ HTTPS
                    ┌──────▼───────┐
                    │  FastAPI     │
                    │  Backend     │
                    └──┬───────┬───┘
                       │       │
              ┌────────▼──┐ ┌──▼────────┐
              │ PostgreSQL │ │   Redis   │
              │  (Data)    │ │ (Cache/Q) │
              └────────────┘ └─────┬─────┘
                                   │
                            ┌──────▼──────┐
                            │ Celery      │
                            │ Worker      │
                            └─────────────┘
```

## Quick Start

### Docker Compose (recommended)

```bash
cp .env.example .env
# Edit .env with your API keys
docker-compose up
```

Services start at:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### Manual Setup

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev      # Watch mode
npm run build    # Production build
npm run serve    # Serve static build
```

**Celery Worker:**
```bash
cd backend
celery -A app.tasks.celery_app worker --loglevel=info
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `REDIS_URL` | Redis connection string | Required |
| `SECRET_KEY` | JWT signing secret | Required |
| `STRIPE_SECRET_KEY` | Stripe API secret key | Required for billing |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret | Required for billing |
| `SPORTSDATA_API_KEY` | SportsData.io API key | Required for data |
| `CORS_ORIGINS` | Comma-separated allowed origins | `http://localhost:3000` |
| `REACT_APP_API_URL` | Backend API URL for frontend | `http://localhost:8000` |

See `.env.example` for a template.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check (DB status, uptime) |
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login (returns JWT) |
| POST | `/api/auth/refresh` | Refresh access token |
| GET | `/api/auth/me` | Current user profile |
| GET | `/api/projections/` | Get player projections |
| POST | `/api/simulations/` | Start Monte Carlo simulation |
| GET | `/api/simulations/{id}` | Get simulation status/results |
| POST | `/api/lineups/optimize` | Generate optimal lineups |
| POST | `/api/billing/create-checkout-session` | Create Stripe checkout |
| POST | `/api/billing/webhook` | Stripe webhook handler |

## Subscription Tiers

| Feature | Free | Pro ($19/mo) | Elite ($49/mo) |
|---------|------|-------------|----------------|
| Simulations | 1,000 | 25,000 | 100,000 |
| Lineups | 5 | 50 | 150 |
| Rate Limit | 10/min | 60/min | 200/min |

## Deployment (Render)

This project includes a `render.yaml` Blueprint for one-click deployment.

1. Push your repo to GitHub
2. Go to [Render Dashboard](https://dashboard.render.com) > **New** > **Blueprint**
3. Connect your repository
4. Render auto-detects `render.yaml` and provisions all services
5. Set manual env vars in the `stacksniper-secrets` group:
   - `STRIPE_SECRET_KEY`
   - `STRIPE_WEBHOOK_SECRET`
   - `SPORTSDATA_API_KEY`
6. Update `CORS_ORIGINS` to your production domain
7. Update `DATABASE_URL` to use `postgresql+asyncpg://` prefix

See `PRODUCTION_CHECKLIST.md` for the full launch checklist.

## Testing

```bash
cd backend
pytest -v --tb=short
```

52 tests covering auth, projections, simulations, lineups, billing, rate limiting, and security.

## Disclaimer

Not gambling advice; for entertainment only. Please play responsibly.
