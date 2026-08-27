# Google sign-in for DESCEND

Google sign-in uses **Supabase Auth** as the middleman. The browser never talks to Google directly with our credentials:

```
/login  →  Google account picker  →  https://<ref>.supabase.co/auth/v1/callback
        →  Supabase trades the code with Google for tokens
        →  https://descendt2dm.me/auth/callback  →  /dashboard
```

Three places must agree. If any one disagrees, sign-in fails at a predictable step.

| Place | What it must contain |
|-------|----------------------|
| Google Cloud | Authorized redirect URI = `https://<ref>.supabase.co/auth/v1/callback` |
| Supabase → Providers → Google | Client ID + Client Secret from that same Google project |
| Supabase → URL Configuration | Site URL + every `/auth/callback` address you use |

---

## Fixing `Unable to exchange external code (unexpected_failure)`

This error means Supabase reached Google's token endpoint and Google refused. Work through the causes in order — they are ordered by how often they are the culprit.

### Cause 1 — the authorization code was already used

Google accepts an authorization code exactly **once**. If the app exchanges it and something exchanges it again, the second attempt fails with this error.

Our client is created with `detectSessionInUrl: true` (`Frontend/src/lib/supabaseClient.ts`), so **supabase-js performs the exchange automatically**. `AuthCallbackPage` must therefore *not* call `exchangeCodeForSession` — it only waits for the session to appear.

Signs you are hitting this: the error appears instantly, and the Supabase Auth logs show two token requests moments apart.

Also note this reproduces more easily in local dev, because React `StrictMode` runs effects twice.

### Cause 2 — Client Secret mismatch

The most common configuration cause. Verify in **Supabase → Authentication → Sign In / Providers → Google**:

1. Confirm **Google enabled** is ON.
2. Re-copy the **Client ID** from Google Cloud → **APIs & Services** → **Credentials** → your OAuth 2.0 Client ID. It ends in `.apps.googleusercontent.com`.
3. In the same Google Cloud screen, click **Add secret** (or reset the existing one) and copy the new **Client Secret** immediately — Google only shows it once.
4. Paste both into Supabase and **Save**.

Watch for these specific mistakes:

- A trailing space or newline from copy-paste (Supabase stores it verbatim)
- Client ID from one Google project, Secret from another
- Using a **Desktop app** or **Android** OAuth client — it must be **Web application**
- Pasting the **API key** instead of the Client Secret

### Cause 3 — redirect URI not registered with Google

In **Google Cloud → Credentials → your OAuth client → Authorized redirect URIs**, this exact value must be present:

```
https://<your-project-ref>.supabase.co/auth/v1/callback
```

Find `<your-project-ref>` in Supabase → **Project Settings** → **General**, or read it from your `VITE_SUPABASE_URL`.

It is **not** your own domain. `https://descendt2dm.me/auth/callback` belongs in Supabase's Redirect URLs, not here.

Google caches OAuth client changes; allow a few minutes and retry in a fresh tab.

### Cause 4 — OAuth consent screen is in Testing mode

**Google Cloud → APIs & Services → OAuth consent screen**. While the app is in **Testing**, only accounts listed under **Test users** can sign in. Either add the Google accounts you are testing with, or **Publish app**.

---

## Other errors and what they mean

| Message | Meaning | Fix |
|---------|---------|-----|
| `Unsupported provider: provider is not enabled` | Google toggle is off in Supabase | Enable it under Sign In / Providers |
| `redirect_uri_mismatch` (shown by Google) | Google does not know the Supabase callback | Cause 3 above |
| `Access blocked: This app's request is invalid` | Same as above, or consent screen incomplete | Causes 3 and 4 |
| "The provider did not return a sign-in code" | Landed on `/auth/callback` with no `code` | Add this exact origin to Supabase Redirect URLs |
| "A sign-in code arrived but no session was created" | PKCE verifier missing for this origin | Started on a different host than it returned to — see below |

### Origin mismatch (www vs non-www)

The PKCE code verifier is stored in browser storage **per origin**. If sign-in starts on `https://descendt2dm.me` but returns to `https://www.descendt2dm.me`, the verifier is not there and no session can be created.

Keep these consistent:

- **Site URL**: `https://descendt2dm.me`
- **Redirect URLs**: include the apex, `www`, the `netlify.app` host, and `http://localhost:5173/auth/callback`
- Ideally redirect `www` → apex at the Netlify level so users only ever use one origin

---

## Reading the actual error

**Supabase → Logs → Auth logs**, filtered to the moment you clicked. This shows the raw provider response, which is more specific than anything the browser displays.

`AuthCallbackPage` also renders the provider's `error_description` on screen, reading it from both the query string and the URL fragment.

---

## Verifying it works

1. Open `https://descendt2dm.me/login` in a **fresh** tab (no leftover `?code=` in the URL)
2. Click **Continue with Google** and pick an account
3. You should land on `/auth/callback` briefly, then `/dashboard`
4. **Supabase → Authentication → Users** shows the user with provider `google`
5. Sign out and back in to confirm it is repeatable

## Notes

- Client ID and Secret live in **Supabase only** — never in Netlify, Vercel, or the repo.
- The button appears on `/login` whenever `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` are set. Set `VITE_ENABLE_GOOGLE_SIGNIN=false` to hide it.
