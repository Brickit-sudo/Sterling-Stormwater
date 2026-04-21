# Deploying Sterling Stormwater to Railway

## Overview
- **Backend** (FastAPI) → Railway service #1, auto-runs Alembic migrations on every deploy
- **Frontend** (Streamlit) → Railway service #2, talks to the backend via env var
- **Database** → Supabase (already live, nothing to change)

---

## One-time setup

### 1. Push to GitHub
```bash
git add .
git commit -m "Add deployment config"
git push origin main
```

### 2. Create Railway account
Go to https://railway.app and sign up (free tier works to start).

### 3. Deploy the backend

1. In Railway dashboard: **New Project → Deploy from GitHub repo**
2. Select this repo, set **Root Directory** to `backend`
3. Railway will detect the Dockerfile automatically
4. Add environment variables (Settings → Variables):

| Variable | Value |
|----------|-------|
| `DATABASE_URL` | Your Supabase connection string (port 6543 for transaction pooler) |
| `JWT_SECRET` | Your secret key (from backend/.env) |
| `ALGORITHM` | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` |

5. Copy the backend's public URL (e.g. `https://sterling-backend.up.railway.app`)

### 4. Deploy the frontend

1. In same Railway project: **New Service → GitHub Repo**
2. Same repo, set **Root Directory** to `stormwater_app`
3. Add environment variable:

| Variable | Value |
|----------|-------|
| `BACKEND_URL` | The backend URL from step 3 (no trailing slash) |

4. Add a **Volume** (Settings → Volumes):
   - Mount path: `/app/projects`  ← uploaded photos/files persist here

5. Your frontend URL is shared with your team. Done.

---

## Updating the app

```bash
# Make changes locally, test, then:
git add .
git commit -m "your message"
git push origin main
# Railway auto-redeploys in ~60 seconds
```

---

## Local testing with Docker

Requires Docker Desktop installed.

```bash
# From repo root:
docker-compose up --build

# Frontend: http://localhost:8501
# Backend:  http://localhost:8000/docs
```

---

## Giving team members access

Share the Railway frontend URL. They log in with their email/password.
To create accounts, use the seed script or the admin panel (if built).

Currently a default account exists:
- Email: `brolfe@sterlingstormwater.com`
- Password: `changeme123` ← change this before going live

To add teammates, hit `POST /auth/register` on the backend or build an admin UI.
