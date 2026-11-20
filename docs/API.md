# HulagwAI HTTP API (v1)

Base: `/api/v1` · JSON · cookie session + CSRF (same-origin). In the browser use `resources/js/api/*.js`, which already does this.
Outside a browser: `GET /` once to receive the `XSRF-TOKEN` + session cookies, then send the cookie jar and header `X-XSRF-TOKEN: <urldecoded cookie value>` on every non-GET call, with `Accept: application/json`.

Errors are always JSON: `{"code": "...", "message": "..."}` (validation errors: `{"message","errors":{field:[...]}}`).
Rate limits answer `429` (`Retry-After` header).

## Identity
| Call | Notes |
|---|---|
| `GET /me` | `{authenticated, user:{id,name,email,has_password,google_connected}\|null, auth:{google:bool}, history_mode:"account"\|"session", quota:{used_bytes,limit_bytes,remaining_bytes}\|null, notice:{privacy}, upload:{max_bytes,extensions}}` |
| `POST /register` *(root path, not /api)* | `{name,email,password,password_confirmation}` → `{user}`. Password ≥ 10 chars, upper+lower+digit. |
| `POST /login` *(root path)* | `{email,password}` → `{user}`. 5 failures / 5 min per email+IP → `429`. |
| `POST /logout` *(root path)* | |
| `POST /api/v1/account/delete` | `{password}` → erases the account and all images. Google-only accounts (no password) confirm with their account email in the same field. |
| `PUT /api/v1/account/profile` · `PUT /api/v1/account/password` | `{name,email}` · `{current_password,password,password_confirmation}` (`current_password` is not needed when the account has no password yet). |
| `POST /forgot-password` *(root path)* | `{email}` → always `{ok:true,message}` (no account enumeration). Emails a reset link built from `APP_URL`, valid 60 min, single use. 5/h per IP, 3/h per email. |
| `POST /reset-password` *(root path)* | `{token,email,password,password_confirmation}` → `{ok,message}`; `422` if the link is invalid/expired. Revokes remember-me and browser-extension tokens. |
| `GET /auth/google/redirect` → `GET /auth/google/callback` *(root path, full-page navigation)* | Google sign-in (OAuth 2.0 code flow + PKCE + state). Signs in, creates an account (no password) or links Google to an existing account with the same **verified** email; when already signed in it links Google to the current account. Failures redirect to `/login?error=google_*`. Needs `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET`. |
| `DELETE /api/v1/account/google` | Unlinks Google; `422 password_required` if the account has no password. |

## Analyses
### `POST /analyses` — multipart field `image`
Limits: JPG/JPEG/PNG/WEBP, ≤ 5 MB, 16–8192 px sides, ≤ 40 MP. Returns **202**:
```json
{ "id":"01J...ULID", "status":"queued", "stage":"queued", "progress":5,
  "steps":[{"key":"image_prepared","label":"Image prepared","state":"up_next"},
           {"key":"visual_pattern_analysis","label":"Visual pattern analysis","state":"up_next"},
           {"key":"generating_prediction","label":"Generating prediction","state":"up_next"}],
  "file":{"filename":"sample_image.png","name":"sample_image","format":"PNG","size_bytes":1070000,"size_mb":1.02,"width":1920,"height":1080},
  "links":{"self":"...","preview":"...","thumb":"...","report":"..."} }
```
Other statuses: `422` invalid image (`errors.image`), `413 quota_exceeded` (`used_bytes`,`limit_bytes`), `429 too_many_pending`, `503 busy`.
Re-uploading an identical image (signed-in) returns **200** with the finished result and `"duplicate": true`.

### `GET /analyses/{id}` — poll every ~700 ms
`status`: `queued → preprocessing → analyzing → finalizing → done` (or `failed` with `error:{code,message}`). `steps[].state`: `complete | in_progress | up_next`.
When `done`:
```json
{ "...": "same fields as above",
  "result":{ "verdict":"ai_generated|real|inconclusive","label":"Likely AI-generated",
            "ai_probability":0.88,"real_probability":0.12,"ai_percent":88,"real_percent":12,
            "confidence":0.88,"confidence_percent":88,
            "explanation":"...","how_to_read":"...","warnings":["upscaled_for_analysis"],
            "decision_source":"model|provenance","findings":[{"id","severity","title","evidence"}],
            "components":{"clip":{"p","weight","role"},"cnn":{...},"frequency":{...}} },
  "analyzed_at":"2026-11-10T08:15:00+00:00","persisted":true }
```
Unknown or not-yours ids always return `404` (never `403`).

#### New in `result` (since v1.1): which generator, and why it looks AI
```json
"attribution": {
  "available": true, "source": "model|metadata", "decision": "family|unknown",
  "headline": "Midjourney",                       // "Unknown generator" when decision = unknown
  "top": [{"family":"midjourney","label":"Midjourney","p":0.71,"percent":71}, {"family":"flux","label":"FLUX","p":0.2,"percent":20}],
  "note": "", "disclaimer": "Generator attribution is a closed-set estimate ..."
},
"evidence": {
  "flags": [{"id":"signal_cnn","category":"Pixel-level texture","strength":"strong|moderate|weak",
             "title":"Pixel-level texture signal","detail":"...","source":"cnn"}],
  "regions": [{"x":0.0,"y":0.0,"w":0.5,"h":0.5,"score":0.91,"where":"upper-left"}],   // fractions of width/height
  "heatmap": {"available": true, "grid": [2,2], "scores": [[0.91,0.2],[0.1,0.3]],
              "image_url": "/api/v1/analyses/{id}/image?variant=heatmap"},          // null when no heat map
  "note": "These are signals ... not proof of a flaw."
}
```
* `attribution.available = false` comes with a `reason`: `not_ai_generated`, `attribution_model_not_installed`, `not_computed` (older analyses) …
* `source = "metadata"` means the file itself names the generator (C2PA, EXIF/XMP, SD-WebUI / ComfyUI data) — that wins over the model.
* Flags with `category = "Limitations"` describe what *weakens* the evidence (small, compressed, upscaled image). Show them separately.
* Evidence never claims specific visual defects (extra fingers, garbled text) — show `note` next to it.
* The heat map exists only when AI is plausible (P(AI) ≥ 0.4) and the image fits at least two 224 px patches (≥ 448 px on one side); smaller images get no location information.

### `GET /analyses/{id}/image?variant=preview|thumb|heatmap` → `image/jpeg`
Re-encoded copy (metadata stripped). Guests only get the 480 px `thumb` and the `heatmap` (both kept in their session).
### `GET /analyses/{id}/report` → `application/pdf`
### `DELETE /analyses/{id}` — cancels a running analysis or deletes a finished one.

## History
### `GET /history?search=&result=all|real|ai_generated|inconclusive&range=all|7d|30d|90d&sort=newest|oldest|confidence_desc|confidence_asc&page=1&per_page=6`
```json
{ "data":[{"id","filename","format","verdict","label","ai_probability","confidence_percent","analyzed_at","thumb_url","result_url"}],
  "meta":{"page","per_page","total","last_page","from","to"},
  "stats":{"total","likely_real","ai_generated","inconclusive"} }
```
Same shape for guests (session) and users (MySQL).
### `GET /history/export?format=csv|json` · `DELETE /history`

## Browser extension (test prototype)
The browser extension (image scanner) uses a short-lived pairing code rather than web-session cookies:

- `POST /api/v1/extension/pair` (signed-in web session + CSRF) creates a single-use 32-character code valid for 3 minutes. The signed-in pairing page is `/extension/connect`.
- `POST /api/v1/extension/exchange` (`{"code":"..."}`) consumes the code once and returns a random bearer token, valid for 30 days. Only a SHA-256 hash is stored server-side.
- `POST /api/v1/extension/analyses` (multipart `image`) and `GET /api/v1/extension/analyses/{id}` require `Authorization: Bearer <token>` and reuse the regular analysis pipeline.
- `DELETE /api/v1/extension/token` revokes the current extension token.

The exchange, extension upload/poll, and revoke endpoints bypass cookie CSRF validation because they require a one-time code or bearer token. Keep the token private; never put it in logs. The extension only scans images the user picks from the right-click menu, after a confirmation click.

## Misc
`GET /model` (active model summary for the About page) · `GET /health` (`{app, ml:{status,model_loaded,metadata_only}}`).
