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

- [Risk scoring](docs/RISK_SCORING.md)
- [Deploy (GitHub → Netlify + Vercel + Supabase)](docs/DEPLOY.md)
- [Custom domain descendt2dm.me (Namecheap)](docs/CUSTOM_DOMAIN.md)
- [Resend email confirmation (Supabase SMTP)](docs/RESEND_EMAIL.md)
