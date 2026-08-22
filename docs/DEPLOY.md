# DESCEND — Detailed Setup Guide (Supabase + Vercel + Netlify)

**Repo:** [https://github.com/Lance0519/DESCEND](https://github.com/Lance0519/DESCEND)

| Piece | Platform | Root folder in repo |
|-------|----------|---------------------|
| Database + Auth | [Supabase](https://supabase.com) | `supabase/migrations/` (SQL only) |
| API (Flask / ML) | [Vercel](https://vercel.com) | `Backend` |
| Website (React) | [Netlify](https://netlify.com) | `Frontend` |

**Do this order:** Supabase first → Vercel second → Netlify third → Google Sign-In last (needs Netlify URL).

Read-aloud uses the **free browser Web Speech API** — no TTS API keys.

Never paste **service_role** or **JWT secret** into Netlify or the browser. Those belong on Vercel / Backend only.

---

## A. Supabase — what to get and what to set

### A1. Create the project

1. Go to [https://supabase.com](https://supabase.com) → Sign in → **New project**.
2. Fill in:
   - **Name:** e.g. `descend`
   - **Database password:** save it somewhere safe (you need it for the Postgres URI).
   - **Region:** closest to you.
3. Wait until the project is ready.

### A2. What to **copy** from Supabase (Settings → API)

Open **Project Settings** (gear) → **API**.

| What you see in Supabase | Copy this value | You will paste it into… |
|--------------------------|-----------------|-------------------------|
| **Project URL** | `https://xxxxx.supabase.co` | Netlify `VITE_SUPABASE_URL` **and** Vercel `SUPABASE_URL` |
| **anon** `public` key | long `eyJ...` key labeled **anon** | Netlify `VITE_SUPABASE_ANON_KEY` only |
| **service_role** `secret` key | long `eyJ...` key labeled **service_role** | Vercel `SUPABASE_SERVICE_ROLE_KEY` only (optional but useful) |
| **JWT Secret** | under JWT Settings / Legacy JWT secret | Vercel `SUPABASE_JWT_SECRET` |

Also get the **database connection string**:

1. **Project Settings** → **Database** → **Connection string** → URI.
2. Replace `[YOUR-PASSWORD]` with the database password you chose.
3. Example shape:  
   `postgresql://postgres.xxxxx:YOUR_PASSWORD@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres`  
   For SQLAlchemy on Vercel, prefer a URI like:  
   `postgresql+psycopg2://...` or `postgresql://...`  
   If the app expects SQLAlchemy MySQL/SQLite style, you can also use:  
   `SQLALCHEMY_DATABASE_URI` = that Postgres URI (add driver if needed later).

### A3. Run the SQL migration (what to input)

1. In Supabase left sidebar → **SQL Editor** → **New query**.
2. Open this file from the repo: [`supabase/migrations/001_descend_schema.sql`](../supabase/migrations/001_descend_schema.sql).
3. Paste the **entire** file into the editor → **Run**.
4. Confirm no errors (creates `profiles`, `assessments`, `assessment_drafts` + RLS).

### A4. Auth URL configuration (what to input)

**Authentication** → **URL Configuration**:

| Field | What to put (start with local; update after Netlify) |
|-------|------------------------------------------------------|
| **Site URL** | For now: `http://localhost:5173` — later change to `https://YOUR-SITE.netlify.app` |
| **Redirect URLs** | Add **both** lines (one per line): |

```
http://localhost:5173/auth/callback
https://YOUR-SITE.netlify.app/auth/callback
```

(Replace `YOUR-SITE` after Netlify gives you a URL.)

### A5. Enable Email auth

**Authentication** → **Providers** → **Email** → enable → Save.

### A6. Enable Google Sign-In (free) — what to get from Google, what to put in Supabase

#### On Google Cloud Console ([console.cloud.google.com](https://console.cloud.google.com/))

1. Create/select a project.
2. **APIs & Services** → **OAuth consent screen** → configure (External is fine for thesis) → add your email as test user if in Testing mode.
3. **Credentials** → **Create credentials** → **OAuth client ID**.
4. Application type: **Web application**.
5. **Authorized redirect URIs** — add **exactly**:

```
https://YOUR-PROJECT-REF.supabase.co/auth/v1/callback
```

`YOUR-PROJECT-REF` is the subdomain from your Project URL  
(e.g. URL `https://tcifzmx…supabase.co` → ref is `tcifzmx…`).

6. Create → **copy**:
   - **Client ID**
   - **Client Secret**

#### On Supabase

1. **Authentication** → **Providers** → **Google**.
2. Turn **Enable Sign in with Google** ON.
3. Paste:
   - **Client ID** ← from Google
   - **Client Secret** ← from Google
4. Save.

Google Client ID/Secret stay in **Supabase only**. Do not put them in Netlify or Vercel env vars for this app.

---

## B. Vercel — Backend API (Flask)

Open [https://vercel.com](https://vercel.com) → **Add New** → **Project** → Import **Lance0519/DESCEND**.

### B1. Project settings (what to input on the form)

| Setting | What to put |
|---------|-------------|
| **Framework Preset** | **Other** (or Flask if listed — do **not** point Flask at Frontend) |
| **Root Directory** | Click Edit → set to **`Backend`** (not `Frontend`) |
| **Build Command** | leave default / empty (uses `Backend/vercel.json`) |
| **Output Directory** | leave empty |
| **Install Command** | leave default |

### B2. Environment Variables — what to put in Key / Value

Click **Environment Variables**. Remove any placeholder like `EXAMPLE_NAME`.

Add **each** row (Environment: Production and Preview is fine):

| Key (exact name) | Value — where to get it |
|------------------|-------------------------|
| `SECRET_KEY` | Make one up: long random string (e.g. password generator, 32+ chars) |
| `FLASK_ENV` | `production` |
| `FRONTEND_ORIGIN` | After Netlify exists: `https://YOUR-SITE.netlify.app` — for first deploy you can use `http://localhost:5173` and update later |
| `SUPABASE_URL` | Supabase **Project URL** (`https://xxxx.supabase.co`) |
| `SUPABASE_JWT_SECRET` | Supabase **JWT Secret** |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase **service_role** key (optional) |
| `SQLALCHEMY_DATABASE_URI` | Supabase Database **URI** (with your DB password filled in). If deploy fails on DB, you can omit this for a temporary SQLite fallback only on local machines — production should use Postgres. |

**Do not add:** `GOOGLE_TTS_API_KEY`, Google OAuth Client ID/Secret.

### B3. Deploy and **what to copy** from Vercel

1. Click **Deploy**.
2. When done, open the deployment → copy the site URL, e.g.:

```
https://descend-xxxxx.vercel.app
```

3. Save this as your **API base URL** (no trailing slash).  
   You will paste it into Netlify as `VITE_API_BASE_URL`.

4. Quick test in browser:  
   `https://YOUR-VERCEL-URL/api/health`  
   (should return JSON if health route is live).

---

## C. Netlify — Frontend (React)

Open [https://app.netlify.com](https://app.netlify.com) → **Add new site** → **Import an existing project** → GitHub → **Lance0519/DESCEND**.

### C1. Build settings (what to input)

If the root `netlify.toml` is detected, many fields auto-fill. Confirm:

| Setting | What to put |
|---------|-------------|
| **Base directory** | `Frontend` |
| **Build command** | `npm run build` |
| **Publish directory** | `Frontend/dist` if base is repo root **or** `dist` if base is already `Frontend` (match what Netlify UI shows; with our `netlify.toml` base=`Frontend`, publish=`dist`) |
| **Node version** | 20 (set in `netlify.toml`) |

### C2. Environment Variables — what to put in Key / Value

Site settings → **Environment variables** → Add:

| Key (exact name) | Value — where to get it |
|------------------|-------------------------|
| `VITE_API_BASE_URL` | Vercel URL from B3, e.g. `https://descend-xxxxx.vercel.app` (**no** `/` at the end) |
| `VITE_SUPABASE_URL` | Supabase **Project URL** |
| `VITE_SUPABASE_ANON_KEY` | Supabase **anon public** key only |

**Do not add** service_role or JWT secret on Netlify.

### C3. Deploy and **what to copy** from Netlify

1. **Deploy site**.
2. Copy the site URL, e.g.:

```
https://YOUR-SITE.netlify.app
```

3. Go back and **update**:
   - **Vercel** env `FRONTEND_ORIGIN` = that Netlify URL → Redeploy Backend.
   - **Supabase** Auth → URL Configuration:
     - Site URL = Netlify URL
     - Redirect URLs include `https://YOUR-SITE.netlify.app/auth/callback`

---

## D. Cheat sheet — who gets what

```text
FROM SUPABASE YOU COPY:
  Project URL          →  Netlify VITE_SUPABASE_URL
                       →  Vercel  SUPABASE_URL
  anon key             →  Netlify VITE_SUPABASE_ANON_KEY
  service_role key     →  Vercel  SUPABASE_SERVICE_ROLE_KEY
  JWT Secret           →  Vercel  SUPABASE_JWT_SECRET
  Database URI         →  Vercel  SQLALCHEMY_DATABASE_URI

FROM GOOGLE CLOUD YOU COPY:
  OAuth Client ID      →  Supabase Auth → Google → Client ID
  OAuth Client Secret  →  Supabase Auth → Google → Client Secret

FROM VERCEL YOU COPY:
  Deployment URL       →  Netlify VITE_API_BASE_URL

FROM NETLIFY YOU COPY:
  Site URL             →  Vercel FRONTEND_ORIGIN
                       →  Supabase Site URL + Redirect URL
```

---

## E. Local development (optional)

`Frontend/.env.local`:

```
VITE_API_BASE_URL=http://127.0.0.1:5000
VITE_SUPABASE_URL=https://xxxx.supabase.co
VITE_SUPABASE_ANON_KEY=eyJ...anon...
```

`Backend/.env`:

```
FLASK_ENV=development
FLASK_PORT=5000
FRONTEND_ORIGIN=http://localhost:5173
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_JWT_SECRET=your-jwt-secret
SUPABASE_SERVICE_ROLE_KEY=eyJ...service_role...
SQLALCHEMY_DATABASE_URI=postgresql://...
SECRET_KEY=dev-secret
```

Run:

```bash
# Backend
cd Backend
python run.py

# Frontend
cd Frontend
npm install
npm run dev
```

---

## F. Final smoke test

1. Open Netlify URL → Start Assessment → **Continue as guest** → finish survey → see Results + descendants.
2. Refresh mid-survey → Resume / Start over works.
3. Access → **Continue with Google** → sign in → Profile shows Google.
4. Tagalog Speak uses device Web Speech (install a Filipino voice on Windows if needed).
5. Browser Network tab: predict calls go to your Vercel `/api/predict`.

---

## Common mistakes

| Mistake | Fix |
|---------|-----|
| Vercel Root Directory = `Frontend` | Change to **`Backend`** |
| Netlify missing `VITE_` prefix | Keys must start with `VITE_` or the browser never sees them |
| Trailing slash on `VITE_API_BASE_URL` | Use `https://xxx.vercel.app` not `...app/` |
| Google redirect wrong | Must be `https://<ref>.supabase.co/auth/v1/callback` |
| Google button missing on Access | Netlify missing `VITE_SUPABASE_URL` / `VITE_SUPABASE_ANON_KEY` → redeploy after adding |
| Putting service_role in Netlify | Remove it — browser must only use **anon** key |
