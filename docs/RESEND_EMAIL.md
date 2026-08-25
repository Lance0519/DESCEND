# Resend for DESCEND email confirmation

DESCEND uses **Supabase Auth** for signup. Confirmation and password-reset emails are sent by Supabase. Point Supabase **custom SMTP** at **Resend** so those messages leave through Resend (higher limits, better deliverability) instead of Supabase’s built-in mailer.

You do **not** put a Resend API key in the Netlify frontend. SMTP is configured only in the Supabase dashboard.

## 1. Resend account

1. Create an account at [https://resend.com](https://resend.com).
2. **API Keys** → **Create API Key** → copy `re_...` (you will paste this as the SMTP password).
3. **Domains** (recommended for production):
   - Add your domain (or a subdomain like `mail.yourdomain.com`).
   - Add the DNS records Resend shows (SPF / DKIM).
   - Wait until the domain shows **Verified**.
4. **For quick testing only:** you can send from `onboarding@resend.dev` to **your own** Resend account email. Production signups need a verified domain.

## 2. Supabase Auth — keep Confirm email ON

**Authentication** → **Providers** → **Email**:

| Setting | Value |
|---------|--------|
| Enable Email provider | ON |
| **Confirm email** | **ON** (required for confirmation links) |

## 3. Supabase — Custom SMTP (Resend)

**Project Settings** → **Authentication** → **SMTP Settings** (or **Auth** → **SMTP**):

| Field | Value |
|-------|--------|
| Enable custom SMTP | ON |
| Sender email | `noreply@YOUR_VERIFIED_DOMAIN` (or `onboarding@resend.dev` while testing) |
| Sender name | `DESCEND` |
| Host | `smtp.resend.com` |
| Port | `465` |
| Username | `resend` |
| Password | your Resend API key (`re_...`) |

Save.

## 4. Redirect URLs (confirmation link target)

**Authentication** → **URL Configuration**:

| Field | Value |
|-------|--------|
| Site URL | `https://descendt2dm.me` (or `https://descendt2dm.netlify.app` until the custom domain is live) |
| Redirect URLs | include: |

```
http://localhost:5173/auth/callback
https://descendt2dm.me/auth/callback
https://www.descendt2dm.me/auth/callback
https://descendt2dm.netlify.app/auth/callback
```

Custom domain DNS (Namecheap → Netlify) and Resend domain verification: **[CUSTOM_DOMAIN.md](CUSTOM_DOMAIN.md)**.

Signup already uses `emailRedirectTo: {origin}/auth/callback`. That page runs `verifyOtp` / session exchange and creates the `profiles` row.

## 5. Optional — email template text

**Authentication** → **Email Templates** → **Confirm signup**.

Keep Supabase’s confirmation link variable. Example body:

```html
<h2>Confirm your DESCEND account</h2>
<p>Thanks for registering. Open this link to finish creating your account:</p>
<p><a href="{{ .ConfirmationURL }}">Confirm email</a></p>
<p>If you did not create an account, you can ignore this message.</p>
```

Same idea for **Reset password** (`{{ .ConfirmationURL }}`).

## 6. Test

1. Register a **new** email on https://descendt2dm.netlify.app/register  
2. Check inbox (and spam) for the message from your Resend sender  
3. Open the link → should land on `/auth/callback` → dashboard or sign-in  
4. In Resend → **Emails**, confirm the message was delivered  

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Still hitting Supabase “email rate limit” | Custom SMTP is off or not saved — Resend SMTP must be enabled |
| Email never arrives | Domain not verified, or testing only allowed to your Resend login email with `onboarding@resend.dev` |
| Link opens but auth fails | Add `https://descendt2dm.netlify.app/auth/callback` under Redirect URLs; Site URL should be the Netlify site |
| 401 after confirm | Confirm email succeeded; sign in again if the session was not stored |

## What the app already does

- `signUp(..., emailRedirectTo: /auth/callback)`
- `AuthCallbackPage` verifies the token and upserts `profiles`
- Register screen shows “confirm your email” when Supabase requires confirmation

No frontend env vars are required for Resend.
