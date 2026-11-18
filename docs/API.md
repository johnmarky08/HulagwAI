# HulagwAI HTTP API (v1)

Base: `/api/v1` · JSON · cookie session + CSRF (same-origin). In the browser use `resources/js/api/*.js`, which already does this.
Outside a browser: `GET /` once to receive the `XSRF-TOKEN` + session cookies, then send the cookie jar and header `X-XSRF-TOKEN: <urldecoded cookie value>` on every non-GET call, with `Accept: application/json`.

Errors are always JSON: `{"code": "...", "message": "..."}` (validation errors: `{"message","errors":{field:[...]}}`).
Rate limits answer `429` (`Retry-After` header).

## Identity
| Call | Notes |
|---|---|
| `GET /me` | `{authenticated, user, history_mode:"account"\|"session", quota:{used_bytes,limit_bytes,remaining_bytes}\|null, upload:{max_bytes,extensions}}` |
| `POST /register` *(root path, not /api)* | `{name,email,password,password_confirmation}` → `{user}`. Password ≥ 10 chars, upper+lower+digit. |
| `POST /login` *(root path)* | `{email,password}` → `{user}`. 5 failures / 5 min per email+IP → `429`. |
| `POST /logout` *(root path)* | |
| `POST /api/v1/account/delete` | `{password}` → erases the account and all images. |

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

### `GET /analyses/{id}/image?variant=preview|thumb` → `image/jpeg`
Re-encoded copy (metadata stripped). Guests only get the 480 px `thumb`.
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

## Misc
`GET /model` (active model summary for the About page) · `GET /health` (`{app, ml:{status,model_loaded}}`).
