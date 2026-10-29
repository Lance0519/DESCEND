# DESCEND

Diabetes risk awareness tool (educational, non-diagnostic) — bilingual English / Tagalog.

## Structure

- `Frontend/` — React + Vite + TypeScript (Netlify)
- `Backend/` — Flask ML API (Vercel)
- `docs/` — Risk scoring + deploy docs
- `supabase/migrations/` — Postgres schema + RLS

## Local development

```bash
# Frontend
cd Frontend
npm install
npm run dev

# Backend
cd Backend
pip install -r requirements.txt
# optional: tests + training merge script
pip install -e ".[dev,scripts]"
python run.py
```

Copy `Frontend/.env.example` and `Backend/.env.example` (see `docs/DEPLOY.md`).

When developing locally, if `SQLALCHEMY_DATABASE_URI`, `DATABASE_URL`, or the
MySQL variables point to an unavailable online database, the backend
automatically switches to `Backend/instance/t2dm_dev.db`. Set
`DATABASE_FAILOVER_TO_SQLITE=false` in `Backend/.env` to disable this fallback
and fail fast instead. The fallback is disabled on Vercel.

## Docs

- [Survey cleaning for training](docs/DATA_CLEANING.md)
- [Google Form field inventory](docs/GOOGLE_FORM_FIELD_INVENTORY.md)
- [ML validation plan](docs/ML_VALIDATION_AND_DOCUMENTATION_PLAN.md)
- [Risk scoring](docs/RISK_SCORING.md)
- [Calculation README](docs/CALCULATION_README.md)
- [Clinician factor percentages (endocrinology handout)](docs/CLINICIAN_FACTOR_PERCENTAGES.md)
- [Deploy (GitHub → Netlify + Vercel + Supabase)](docs/DEPLOY.md)
- [Custom domain descendt2dm.me (Namecheap)](docs/CUSTOM_DOMAIN.md)
- [Resend email confirmation (Supabase SMTP)](docs/RESEND_EMAIL.md)
