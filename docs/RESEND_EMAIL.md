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

## 5. Branded email templates (Supabase)

**Authentication** → **Emails** → **Templates**.

Custom SMTP must already be enabled (otherwise Supabase locks template editing).

Keep Supabase variables exactly: `{{ .ConfirmationURL }}`, `{{ .SiteURL }}`, `{{ .Email }}`.

### Confirm sign up — Subject

```text
Confirm your DESCEND account
```

### Confirm sign up — Body

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Confirm your DESCEND account</title>
</head>
<body style="margin:0;padding:0;background:#eef4f1;font-family:Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#1f2937;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#eef4f1;padding:32px 12px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:560px;background:#ffffff;border:1px solid #d7e3dc;border-radius:16px;overflow:hidden;">
          <tr>
            <td style="background:#1f6f5b;padding:28px 32px;">
              <p style="margin:0;font-size:13px;letter-spacing:0.08em;text-transform:uppercase;color:#c8ebe0;">Diabetes risk awareness</p>
              <h1 style="margin:8px 0 0;font-size:28px;line-height:1.2;color:#ffffff;font-weight:700;">DESCEND</h1>
            </td>
          </tr>
          <tr>
            <td style="padding:32px;">
              <h2 style="margin:0 0 12px;font-size:22px;line-height:1.3;color:#16352c;">Confirm your email</h2>
              <p style="margin:0 0 16px;font-size:16px;line-height:1.6;color:#374151;">
                Thanks for creating an account. Confirm your email to finish setup and open your dashboard.
              </p>
              <p style="margin:0 0 24px;font-size:14px;line-height:1.5;color:#6b7280;">
                Signed up as <strong style="color:#16352c;">{{ .Email }}</strong>
              </p>
              <table role="presentation" cellspacing="0" cellpadding="0" style="margin:0 0 24px;">
                <tr>
                  <td style="border-radius:10px;background:#1f6f5b;">
                    <a href="{{ .ConfirmationURL }}" style="display:inline-block;padding:14px 22px;font-size:16px;font-weight:700;color:#ffffff;text-decoration:none;">
                      Confirm email
                    </a>
                  </td>
                </tr>
              </table>
              <p style="margin:0 0 8px;font-size:13px;line-height:1.5;color:#6b7280;">
                If the button does not work, copy and paste this link into your browser:
              </p>
              <p style="margin:0 0 24px;font-size:12px;line-height:1.5;word-break:break-all;color:#1f6f5b;">
                {{ .ConfirmationURL }}
              </p>
              <p style="margin:0;font-size:13px;line-height:1.55;color:#6b7280;">
                DESCEND is an educational awareness tool, not a medical diagnosis. If you did not create this account, you can ignore this message.
              </p>
            </td>
          </tr>
          <tr>
            <td style="padding:18px 32px;background:#f7faf8;border-top:1px solid #e5eee9;">
              <p style="margin:0;font-size:12px;line-height:1.5;color:#6b7280;">
                <a href="{{ .SiteURL }}" style="color:#1f6f5b;text-decoration:none;font-weight:600;">descendt2dm.me</a>
                · DESCEND
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
```

### Reset password — Subject

```text
Reset your DESCEND password
```

### Reset password — Body

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Reset your DESCEND password</title>
</head>
<body style="margin:0;padding:0;background:#eef4f1;font-family:Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#1f2937;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#eef4f1;padding:32px 12px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:560px;background:#ffffff;border:1px solid #d7e3dc;border-radius:16px;overflow:hidden;">
          <tr>
            <td style="background:#1f6f5b;padding:28px 32px;">
              <p style="margin:0;font-size:13px;letter-spacing:0.08em;text-transform:uppercase;color:#c8ebe0;">Account security</p>
              <h1 style="margin:8px 0 0;font-size:28px;line-height:1.2;color:#ffffff;font-weight:700;">DESCEND</h1>
            </td>
          </tr>
          <tr>
            <td style="padding:32px;">
              <h2 style="margin:0 0 12px;font-size:22px;line-height:1.3;color:#16352c;">Reset your password</h2>
              <p style="margin:0 0 24px;font-size:16px;line-height:1.6;color:#374151;">
                We received a request to reset the password for <strong>{{ .Email }}</strong>. Open the button below to choose a new password.
              </p>
              <table role="presentation" cellspacing="0" cellpadding="0" style="margin:0 0 24px;">
                <tr>
                  <td style="border-radius:10px;background:#1f6f5b;">
                    <a href="{{ .ConfirmationURL }}" style="display:inline-block;padding:14px 22px;font-size:16px;font-weight:700;color:#ffffff;text-decoration:none;">
                      Reset password
                    </a>
                  </td>
                </tr>
              </table>
              <p style="margin:0 0 8px;font-size:13px;line-height:1.5;color:#6b7280;">
                If the button does not work, copy and paste this link:
              </p>
              <p style="margin:0 0 24px;font-size:12px;line-height:1.5;word-break:break-all;color:#1f6f5b;">
                {{ .ConfirmationURL }}
              </p>
              <p style="margin:0;font-size:13px;line-height:1.55;color:#6b7280;">
                If you did not ask for a password reset, you can ignore this email. Your password will stay the same.
              </p>
            </td>
          </tr>
          <tr>
            <td style="padding:18px 32px;background:#f7faf8;border-top:1px solid #e5eee9;">
              <p style="margin:0;font-size:12px;line-height:1.5;color:#6b7280;">
                <a href="{{ .SiteURL }}" style="color:#1f6f5b;text-decoration:none;font-weight:600;">descendt2dm.me</a>
                · DESCEND
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
```

Save each template after pasting.

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
