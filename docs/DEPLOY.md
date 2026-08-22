# DESCEND Deploy Guide

Stack (locked):

| Layer | Platform |
|-------|----------|
| Source | GitHub ([Lance0519/DESCEND](https://github.com/Lance0519/DESCEND)) |
| Frontend | Netlify |
| API | Vercel (Python serverless wrapping Flask) |
| DB / Auth | Supabase (Postgres + Google / email) |

Read-aloud uses the **free browser Web Speech API** (no Google Cloud TTS).

## 1. GitHub

Repo: `https://github.com/Lance0519/DESCEND`

1. Push to `main` (production).
2. Ensure `.gitignore` excludes `.env`, `node_modules`, venvs, and databases.
3. Never commit secrets (Supabase service role, JWT secret, OAuth client secret).

## 2. Supabase

1. Create a project.
2. Run SQL in `supabase/migrations/001_descend_schema.sql`.
3. Auth → Providers → enable **Email**.
4. Enable **Google** (see section 5 below).
5. Auth → URL configuration:
   - Site URL = your Netlify URL (or `http://localhost:5173` for local)
   - Redirect URLs include:
     - `http://localhost:5173/auth/callback`
     - `https://<your-netlify-site>.netlify.app/auth/callback`
6. Copy **Project URL**, **anon key**, **JWT secret**, **service role** (server only).

## 3. Vercel (Backend)

1. Import the GitHub repo in Vercel.
2. Root directory: `Backend`.
3. Framework: Other; build uses `vercel.json` → `api/index.py`.
4. Environment variables:

| Name | Purpose |
|------|---------|
| `SQLALCHEMY_DATABASE_URI` | Prefer Supabase Postgres URI, or SQLite for smoke tests |
| `SUPABASE_JWT_SECRET` | JWT secret from Supabase settings |
| `SUPABASE_URL` | Project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Server-side only (optional) |
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

## 5. Google Sign-In checklist (free OAuth)

Google Sign-In uses Supabase Auth + a free Google Cloud OAuth client (not paid TTS).

1. Open [Google Cloud Console](https://console.cloud.google.com/) → APIs & Services → Credentials.
2. Create **OAuth 2.0 Client ID** (application type: **Web application**).
3. Authorized redirect URI (exact):
   - `https://<project-ref>.supabase.co/auth/v1/callback`
4. Copy **Client ID** and **Client Secret**.
5. Supabase → Authentication → Providers → **Google** → enable → paste Client ID + Secret → Save.
6. Confirm redirect URLs in Supabase Auth URL config (section 2).
7. Netlify (or local) has `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`.
8. Test:
   - Open site → **Start Assessment** → **Continue with Google**
   - Approve Google account
   - Land on `/assessment` signed in
   - **Profile** shows provider `google`

If the Google button is missing, Supabase env vars are not set on the frontend host.

## 6. Smoke checklist

- [ ] Landing → Access → Guest → full assessment → Results with descendant projections
- [ ] Refresh mid-assessment → Resume / Start over
- [ ] Email register + **Google sign-in** → Profile + History
- [ ] Tagalog Speak uses free Web Speech (Filipino/Tagalog system voice when installed)
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
SUPABASE_URL=https://xxxx.supabase.co
```
