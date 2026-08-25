# Custom domain: descendt2dm.me (Namecheap → Netlify → Supabase → Resend)

Your site stays hosted on **Netlify**. Namecheap only holds the **DNS**.  
API stays on **Vercel** (`https://descendt2dm.vercel.app`) unless you later add `api.descendt2dm.me`.

**Goal:** open `https://descendt2dm.me` and have signup confirmation emails from `@descendt2dm.me`.

---

## 1. Netlify — add the domain

1. [Netlify](https://app.netlify.com) → your DESCEND site → **Domain management** → **Add a domain**.
2. Enter `descendt2dm.me` → verify / add.
3. Also add `www.descendt2dm.me` if Netlify offers it (recommended).
4. Netlify shows DNS records you must create. Typical options:

### Option A — Netlify DNS (simplest)

1. In Netlify domain settings, choose to use **Netlify nameservers**.
2. Copy the 4 nameservers Netlify shows (e.g. `dns1.p03.nsone.net` …).
3. In **Namecheap** → **Domain List** → `descendt2dm.me` → **Domain** → **Nameservers** → **Custom DNS**.
4. Paste Netlify’s nameservers → Save.
5. Wait 15 minutes–48 hours for propagation. Netlify will issue HTTPS automatically.

### Option B — Keep Namecheap DNS (A / CNAME)

In Namecheap → **Advanced DNS** → **Add new record** (remove conflicting parking records first):

| Type | Host | Value | TTL |
|------|------|--------|-----|
| **A Record** | `@` | Netlify load balancer IP (Netlify shows this; often `75.2.60.5`) | Automatic |
| **CNAME** | `www` | `descendt2dm.netlify.app` (or the hostname Netlify shows) | Automatic |

Use the **exact** values Netlify displays for your site — do not guess old IPs if Netlify lists different ones.

Then in Netlify, wait until the domain shows **HTTPS / SSL provisioned**.

---

## 2. Vercel — allow the new frontend origin

**Vercel** → DESCEND Backend project → **Settings** → **Environment Variables**:

| Key | Value |
|-----|--------|
| `FRONTEND_ORIGIN` | `https://descendt2dm.me,https://www.descendt2dm.me,https://descendt2dm.netlify.app` |

Redeploy the Backend after saving.

(The API code also allowlists `descendt2dm.me` in CORS.)

---

## 3. Supabase — auth redirects

**Authentication** → **URL Configuration**:

| Field | Value |
|-------|--------|
| **Site URL** | `https://descendt2dm.me` |
| **Redirect URLs** | add all of these (one per line): |

```
http://localhost:5173/auth/callback
https://descendt2dm.me/auth/callback
https://www.descendt2dm.me/auth/callback
https://descendt2dm.netlify.app/auth/callback
```

Save.

---

## 4. Resend — send mail from @descendt2dm.me

1. [Resend](https://resend.com) → **Domains** → **Add Domain** → `descendt2dm.me`  
   (or a subdomain like `mail.descendt2dm.me` if you prefer).
2. Resend shows **DNS records** (usually TXT for SPF/DKIM, sometimes MX/CNAME).
3. In **Namecheap Advanced DNS** (or Netlify DNS if you switched nameservers), add **every** record Resend lists.
4. Back in Resend → click **Verify**. Wait until status is **Verified**.
5. **Supabase** → Auth **SMTP**:
   - Sender email: e.g. `noreply@descendt2dm.me`
   - Sender name: `DESCEND`
   - Host `smtp.resend.com`, Port `465`, Username `resend`
   - Password: your Resend API key (never commit it)

See also [RESEND_EMAIL.md](RESEND_EMAIL.md).

---

## 5. Optional — `www` → apex redirect

In Netlify domain settings, set primary domain to `descendt2dm.me` and enable redirect from `www` → apex (or the reverse). Pick one primary URL and use that as Supabase **Site URL**.

---

## 6. Smoke test checklist

1. `https://descendt2dm.me` loads the DESCEND site (padlock / HTTPS).
2. Guest assessment still scores (API calls to Vercel work — no CORS errors in DevTools).
3. Register a **new** email → confirmation arrives from `noreply@descendt2dm.me`.
4. Confirmation link opens `https://descendt2dm.me/auth/callback` and finishes signup.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Domain “pending” forever | Nameservers/DNS wrong; wait longer; remove Namecheap parking/URL redirect records |
| HTTPS error | Wait for Netlify certificate; do not force HTTPS until DNS resolves |
| CORS / blocked predict | Set Vercel `FRONTEND_ORIGIN` and redeploy; hard-refresh the site |
| Confirm link goes to old netlify URL | Update Supabase Site URL + Redirect URLs; register again |
| Resend domain not verified | DNS records incomplete or still propagating; re-check in Resend |

You do **not** need to change `VITE_API_BASE_URL` unless you also create a custom API hostname. Keep it as `https://descendt2dm.vercel.app`.
