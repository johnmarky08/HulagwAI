# Security notes (OWASP Top 10 · 2021)

> No system is "non-vulnerable". This is what is implemented, how it was tested, and what remains your job in production.
> Backend tests: `php artisan test` (IDOR, quota races, upload abuse, lockout, CSV injection, encryption-at-rest, tamper detection, account erasure).

| OWASP | Risk | What HulagwAI does |
|---|---|---|
| **A01 Broken access control** | IDOR on image ids | Public ids are 26-char ULIDs (never auto-increment ids). **One** class decides access (`AnalysisAccess`): users → rows they own; guests → ids stored in *their own* session. Anything else is `404` (no existence leak). Every query is scoped by owner; there is no route-model binding. |
| **A02 Cryptographic failures** | plaintext images/names | Images: XChaCha20-Poly1305 (libsodium), key = HKDF(APP_KEY, "filevault"), random nonce per file, AAD = `<id>:<kind>` (a blob copied to another record fails to decrypt). Filenames + result details: Laravel AES-256 + HMAC `encrypted` casts. Sessions encrypted. Passwords: bcrypt (cost 12). IPs are only stored as HMAC. Files live in `storage/app/private` (never web-served). |
| **A03 Injection** | SQL / command / XSS | Eloquent/query builder only (parameterised). PHP never shells out: the ML service is a separate process reached over HTTP. Blade escapes everything in the PDF; Svelte escapes by default; CSV export neutralises `= + - @` formula cells. Strict CSP. Metadata evidence strings are control/bidi-stripped and truncated. |
| **A04 Insecure design** | abuse, quota bypass | Upload quota enforced inside a DB transaction holding a row lock on the user (no race overshoot). Per-IP and per-user rate limits, concurrent-job cap for guests, queue backlog cap, decompression-bomb limits (40 MP / 8192 px) enforced twice (PHP + Pillow). The result page makes clear it is a prediction, not proof. |
| **A05 Security misconfiguration** | headers, debug | CSP, `X-Frame-Options: DENY`, `nosniff`, `Referrer-Policy`, `Permissions-Policy`, COOP/CORP, HSTS (on HTTPS). ML service: no `/docs`, no `/openapi.json`, bound to 127.0.0.1, refuses to start without a ≥ 32-char secret. API errors are always JSON without stack traces. |
| **A06 Vulnerable components** | dependencies | Pinned by `composer.lock` / `package-lock.json`. Run `composer audit`, `npm audit`, `pip-audit` regularly. |
| **A07 Identification & auth failures** | brute force, fixation | Throttle: 5 failed logins / 5 min per email+IP (then 429, even with the right password), 20 req/min/IP on auth routes, 10 sign-ups/h/IP. Session ID regenerated at login; logout invalidates the session. Identical error for "no such user" and "bad password". Password ≥ 10 chars, mixed case + digit (optional HIBP breach check: `PASSWORD_CHECK_BREACHED=true`). HttpOnly + SameSite=Lax cookies. |
| **A08 Software & data integrity** | tampered model files | Model weights are `safetensors` (no pickle → no code execution). The bundle has a SHA-256 manifest verified at start-up; a modified file stops the model from loading. Every analysis stores the weights hash. Laravel validates the ML response schema/ranges/sizes and whitelists keys before storing anything. |
| **A09 Logging & monitoring failures** | no audit trail | `audit_logs` table (register/login/failed/locked/upload/delete/export/report/account-deleted) with HMAC-hashed IP, no filenames/emails. Laravel log level `warning`. |
| **A10 SSRF** | server fetching URLs | The server never fetches user-supplied URLs. The only outbound call is to `ML_SERVICE_URL` from config, with redirects disabled. |

## Known limits / your production checklist
* **HTTPS is mandatory** in production: set `APP_ENV=production`, `APP_DEBUG=false`, `SESSION_SECURE_COOKIE=true`, serve over TLS. (HSTS and the Secure cookie only work on HTTPS.)
* **Database account**: create a dedicated MySQL user with privileges only on the `hulagwai` schema. Never use XAMPP's passwordless `root`.
* **Back up `APP_KEY`** (offline). Losing it makes all stored images/filenames unreadable; rotating it requires re-encrypting data.
* Sign-up reveals whether an email is already registered (needed without email verification). It is rate limited; add email verification if that matters to you.
* The ML service trusts anyone holding the shared secret → keep it on loopback or a private network; never expose port 8001.
* Uploaded originals are parsed by Pillow in the ML process. Keep Pillow updated (image parsers are a classic attack surface). Run the service as an unprivileged user.
* Detection is probabilistic. Do not use a verdict as the sole basis for decisions about people.
* C2PA manifests are detected but **not cryptographically verified**.
* Rate limiting uses the `cache` store (database). Behind a reverse proxy configure trusted proxies so client IPs are correct.
