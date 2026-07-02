# Riot Analytics Platform

A React web app showing League of Legends apex-tier (Challenger / Grandmaster / Master) stats,
backed by a Postgres database that's refreshed daily via an automated GitHub Actions ETL job
that pulls data from the Riot Games API.

- **`frontend/`** — React + Vite + Tailwind app, reads directly from Supabase's auto-generated
  read-only REST API. Deployed on Vercel with automatic CI/CD on every push.
- **`backend/etl/`** — Python ETL pipeline: pulls the apex leaderboard and an incrementally
  rotating slice of match history from the Riot API, respecting Riot's rate limits, and loads it
  into Postgres. Runs daily via [`.github/workflows/daily-etl.yml`](.github/workflows/daily-etl.yml)
  (free, unlimited minutes on this public repo).
- **`database/schema.sql`** — Postgres schema, including the read-only Row-Level-Security
  policies the frontend relies on.

## One-time setup

These steps only need to be done once, by whoever owns the Riot API key / hosting accounts.

### 1. Riot API key

Apply for a **Personal API key** at the [Riot Developer Portal](https://developer.riotgames.com/).
A development key won't work here — it expires every 24 hours and would break the daily
automation. A personal key doesn't expire and has the same rate limit (20 req/1s, 100 req/2min).

### 2. Database (Supabase)

1. Create a free project at [supabase.com](https://supabase.com).
2. In the SQL editor, run [`database/schema.sql`](database/schema.sql).
3. Grab two things from Project Settings:
   - **Database → Connection string (URI)** → this is `DATABASE_URL`, used by the ETL job.
   - **API → Project URL and anon public key** → these are `VITE_SUPABASE_URL` and
     `VITE_SUPABASE_ANON_KEY`, used by the frontend. The anon key is safe to expose client-side;
     it can only read, thanks to the RLS policies in the schema.

### 3. GitHub Actions secrets

In this repo: Settings → Secrets and variables → Actions, add:
- `RIOT_API_KEY`
- `DATABASE_URL`

The daily workflow (`daily-etl.yml`) will start running on schedule once these exist. You can
also trigger it manually from the Actions tab (`workflow_dispatch`).

### 4. Frontend hosting (Vercel)

Import this repo into [Vercel](https://vercel.com) (root directory: `frontend/`). Add the two
`VITE_SUPABASE_*` env vars in the Vercel project settings. Every push to `main` auto-deploys;
PRs get preview deployments.

## Local development

**Backend / ETL:**
```
cd backend
cp .env.example .env   # fill in RIOT_API_KEY and DATABASE_URL
pip install -r requirements.txt
python -m etl.main
```

**Frontend:**
```
cd frontend
cp .env.example .env   # fill in VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY
npm install
npm run dev
```
