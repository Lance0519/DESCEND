# DESCEND Deploy Guide

Stack (locked):

| Layer | Platform |
|-------|----------|
| Source | GitHub |
| Frontend | Netlify |
| API | Vercel (Python serverless wrapping Flask) |
| DB / Auth | Supabase (Postgres + Google / email) |

## 1. GitHub

1. Create a repository (e.g. `descend-t2dm`).
2. Push the contents of `REBUILD OF SYSTEM/` as the repo root (or keep this folder as a monorepo subdirectory and set Netlify/Vercel base paths accordingly).
3. Ensure `.gitignore` excludes `.env`, `node_modules`, venvs, and databases.
4. Use branch `main` for production deploys.

```bash
cd "REBUILD OF SYSTEM"
git init
git add .
git commit -m "Initial DESCEND rebuild"
gh repo create descend-t2dm --private --source=. --remote=origin --push
```

## 2. Supabase

1. Create a project.
2. Run SQL in `supabase/migrations/001_descend_schema.sql`.
3. Auth → Providers → enable **Email** and **Google**.
4. Google Cloud Console: create OAuth client; add redirect URIs:
   - `https://<project-ref>.supabase.co/auth/v1/callback`
5. Supabase Auth URL config: Site URL = Netlify URL; redirect allow list includes:
   - `http://localhost:5173/auth/callback`
   - `https://<your-netlify-site>.netlify.app/auth/callback`
6. Copy **Project URL**, **anon key**, **JWT secret**, **service role** (server only).

## 3. Vercel (Backend)

1. Import the GitHub repo in Vercel.
2. Root directory: `Backend` (if monorepo) or repo root if Backend files are at root.
3. Framework: Other; build uses `vercel.json` → `api/index.py`.
4. Environment variables:

| Name | Purpose |
|------|---------|
| `SQLALCHEMY_DATABASE_URI` | Prefer Supabase Postgres URI, or SQLite for smoke tests |
| `SUPABASE_JWT_SECRET` | JWT secret from Supabase settings |
| `SUPABASE_URL` | Project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Server-side only (optional) |
| `GOOGLE_TTS_API_KEY` | Google Cloud Text-to-Speech API key |
| `FRONTEND_ORIGIN` | `https://<netlify-site>.netlify.app` |
| `SECRET_KEY` | Flask secret |
| `FLASK_ENV` | `production` |

5. Deploy; note the API base URL (e.g. `https://descend-api.vercel.app`).

**Note:** ExtraTrees model artifacts must be present under `Backend/ml/models/`. If the package exceeds Vercel size limits, upload the model to Supabase Storage and load it at cold start (follow-up hardening).

## 4. Netlify (Frontend)

1. Import the same GitHub repo.
2. Base directory: `Frontend` (or use root `netlify.toml`).
3. Build: `npm run build`; publish: `dist`.
4. Environment:

| Name | Value |
|------|-------|
| `VITE_API_BASE_URL` | Vercel API URL (no trailing slash) |
| `VITE_SUPABASE_URL` | Supabase project URL |
| `VITE_SUPABASE_ANON_KEY` | Supabase anon key |

5. Deploy. Confirm SPA redirects send all routes to `index.html`.

## 5. Google Cloud TTS

1. Enable Cloud Text-to-Speech API.
2. Create an API key (restrict to TTS).
3. Set `GOOGLE_TTS_API_KEY` on Vercel.
4. Voices: Tagalog `fil-PH-Wavenet-A`, English `en-US-Neural2-C`.
5. If the key is missing, `/api/tts` returns 204 and the frontend falls back to Web Speech.

## 6. Smoke checklist

- [ ] Landing → Access → Guest → full assessment → Results with descendant projections
- [ ] Refresh mid-assessment → Resume / Start over
- [ ] Email register + Google sign-in → Profile + History
- [ ] Tagalog Speak reads clearly via TTS when key is set
- [ ] CORS allows Netlify origin against Vercel API

## Local env examples

`Frontend/.env.local`:

```
VITE_API_BASE_URL=http://127.0.0.1:5000
VITE_SUPABASE_URL=https://xxxx.supabase.co
VITE_SUPABASE_ANON_KEY=eyJ...
```

`Backend/.env`:

```
FLASK_ENV=development
FLASK_PORT=5000
FRONTEND_ORIGIN=http://localhost:5173
SUPABASE_JWT_SECRET=your-jwt-secret
GOOGLE_TTS_API_KEY=
```
