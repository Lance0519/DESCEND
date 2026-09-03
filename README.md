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
python run.py
```

Copy `Frontend/.env.example` and `Backend/.env.example` (see `docs/DEPLOY.md`).

## Docs

- [Survey cleaning for training](docs/DATA_CLEANING.md)
- [Google Form field inventory](docs/GOOGLE_FORM_FIELD_INVENTORY.md)
- [ML validation plan](docs/ML_VALIDATION_AND_DOCUMENTATION_PLAN.md)
- [Risk scoring](docs/RISK_SCORING.md)
- [Clinician factor percentages (endocrinology handout)](docs/CLINICIAN_FACTOR_PERCENTAGES.md)
- [Deploy (GitHub → Netlify + Vercel + Supabase)](docs/DEPLOY.md)
- [Custom domain descendt2dm.me (Namecheap)](docs/CUSTOM_DOMAIN.md)
- [Resend email confirmation (Supabase SMTP)](docs/RESEND_EMAIL.md)
