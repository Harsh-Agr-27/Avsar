# Avsar

Avsar helps students in India find scholarships, government schemes, and
internships in one place. Users can create an account, fill an optional profile,
and see which opportunities they are eligible for.

- **Backend:** Django (WSGI), server-rendered templates
- **Database:** PostgreSQL in production (any `DATABASE_URL`), SQLite for local
  development
- **Hosting:** [Vercel](https://vercel.com) Functions, configured out of the box

## Deploy to Vercel

### 1. Create the database

In the Vercel dashboard open **Storage → Create Database → Postgres**
(Neon-backed, free tier available), or use any Postgres provider such as
[Neon](https://neon.tech). Connecting it to the project sets `DATABASE_URL`
(and/or `POSTGRES_URL`) automatically for every environment.

Without a database the app still boots and serves the catalogue, but SQLite on
Vercel lives in `/tmp`: data is discarded when the function instance recycles.
Use Postgres for anything real.

### 2. Set the required environment variables

| Variable | Required | Notes |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | **Yes** on Vercel | Required at request time: the app refuses to serve without it and the function logs a clear error. It is *not* needed to build, so the build succeeds without it. Generate with `python -c "import secrets; print(secrets.token_urlsafe(50))"`. |
| `DATABASE_URL` | Recommended | Set automatically by the Vercel Postgres integration. `POSTGRES_URL` also works. |
| `DEBUG` | No | Defaults to `False`. Never enable in production. |
| `ALLOWED_HOSTS` | Only for custom domains | `*.vercel.app` hosts and the deployment URL are trusted automatically. |
| `CSRF_TRUSTED_ORIGINS` | Only for custom domains | e.g. `https://avsar.example.com`. |
| `AUTO_MIGRATE` | No | Defaults to `true`; see [Migrations](#migrations). |

See [`.env.example`](.env.example) for the full list, including optional
hardening such as `SECURE_HSTS_SECONDS`.

### 3. Deploy

**Option A — Vercel CLI**

```bash
npm i -g vercel
vercel            # preview deployment
vercel --prod     # production deployment
```

**Option B — Git integration**

Push the repository to GitHub/GitLab/Bitbucket, then **Add New → Project** in
the Vercel dashboard and import it. Every push to the production branch then
deploys. No dashboard build or output settings are needed: [`vercel.json`](vercel.json)
declares a single [Vercel Service](https://vercel.com/docs/services) named
`avsar` rooted at the `Avsar/` directory. Vercel installs
[`Avsar/requirements.txt`](Avsar/requirements.txt), detects
`Avsar/manage.py`, runs `collectstatic`, and routes every request to the WSGI
app (`Avsar/Avsar/wsgi.py`).

Add `DJANGO_SECRET_KEY` before the first deployment (or immediately after). The
build itself does not need it — Vercel imports settings during the build to find
the entrypoint and to run `collectstatic`, so the requirement lives in the
request path instead. Without it the deployment builds and then returns errors,
with the reason in the function logs.

### 4. Create an admin user (optional)

```bash
# Download the project's environment variables, including DATABASE_URL.
vercel env pull .env.local --environment=production
python Avsar/manage.py createsuperuser
```

The Django admin is available at `/admin/`.

## Migrations

Vercel Functions have no release phase, so `Avsar/Avsar/wsgi.py` calls
`ensure_database_ready()` on cold start. It applies migrations once per
instance, serialised with a Postgres advisory lock, and seeds the opportunity
catalogue from `Avsar/pages/fixtures/opportunities.json` on a fresh database.

To migrate out-of-band (CI, a release step, or just before a deploy):

```bash
vercel env pull .env.local --environment=production
python Avsar/manage.py migrate
```

Running it manually is safe alongside the startup hook because migrations are
idempotent. Set `AUTO_MIGRATE=false` in Vercel if you would rather migrations
only ever run from CI.

Schema changes are ordinary Django migrations — add new files under
`Avsar/pages/migrations/`.

## Local development

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cd Avsar
python manage.py migrate
python manage.py createsuperuser  # optional
python manage.py runserver
```

The site runs at <http://127.0.0.1:8000/>. Without `DATABASE_URL`/`DB_HOST`
Django uses `Avsar/db.sqlite3`.

Environment configuration is optional locally. Copy `.env.example` to
`Avsar/.env` (or the repo-root `.env` / `.env.local`) and set `DEBUG=True` when
you want Django to serve CSS and images itself — with `DEBUG=False`,
`runserver` does not serve static files.

Run the test suite:

```bash
cd Avsar
python manage.py test
```

Or, to run the services exactly as Vercel does (routing included):

```bash
vercel dev                        # or: vercel dev --local
```

## How the deployment is wired

The project is one Django app, so it deploys as a **single Vercel Service**
named `avsar` (`vercel.json` → root `Avsar/`). Services mode is used
rather than a plain project so that additional services (an API, a worker, a
separate frontend) can be added to this repository later without a new
project. There is only one service today, so no service-to-service bindings
are needed.

| Concern | Where it lives |
| --- | --- |
| Service (`avsar`, root `Avsar/`) and public routing | [`vercel.json`](vercel.json) |
| Function config (`maxDuration`, service-relative) | [`vercel.json`](vercel.json) |
| Public path | every request (`/(.*)`) → service `avsar` |
| Python version (3.12) | [`.python-version`](.python-version) |
| Dependencies installed by Vercel | [`Avsar/requirements.txt`](Avsar/requirements.txt) |
| Entrypoint | `Avsar/Avsar/wsgi.py` (detected via `Avsar/manage.py`) |
| Startup migrations + catalogue seed | `Avsar/Avsar/bootstrap.py`, `Avsar/pages/migrations/0003_*` |
| Static files (`/static/`) | `collectstatic` → Vercel CDN, enabled by `STATIC_ROOT` |
| Secrets and `.sqlite3` files | [`.vercelignore`](.vercelignore) |

Four rules keep the build working, and `VercelServicesConfigTests` enforces them:

- **The service root is `Avsar/`, not the repository root.** Vercel looks for
  `manage.py` in the service root and its immediate children, so a service
  rooted at `.` would find the app two levels down and fail with
  `DJANGO_ENTRYPOINT_NOT_FOUND`.
- **`Avsar/requirements.txt` is self-contained.** Vercel installs inside the
  service root and does not resolve `-r ../requirements.txt` includes; that
  fails the build with `could not parse requirements.txt`. Dependencies are
  duplicated there — update both files together. (The root
  [`requirements.txt`](requirements.txt) stays for local `pip install`.)
- **`functions` paths are relative to the service root**, hence
  `"Avsar/wsgi.py"` rather than `"Avsar/Avsar/wsgi.py"`.
- **Settings must import without secrets.** The build runs `manage.py` to
  discover `DJANGO_SETTINGS_MODULE`/`WSGI_APPLICATION` and to run
  `collectstatic`, and it does so *without* project environment variables.
  Raising on a missing `DJANGO_SECRET_KEY` at import time therefore failed the
  build with `DJANGO_SETTINGS_FAILED`. `Avsar.settings` now accepts an empty
  key and `Avsar.bootstrap.require_secret_key()` (called from `wsgi.py` and
  `asgi.py`) enforces it when a request is served. Keep new required
  configuration read lazily for the same reason.

If you later add a second service and one service needs to call another, declare
a [binding](https://vercel.com/docs/services/bindings) on the **calling**
service and read the injected URL in that service's code:

```json
"bindings": [
  { "type": "service", "service": "inventory", "format": "url", "env": "INVENTORY_URL" }
]
```

```python
url = f"{os.environ['INVENTORY_URL']}/items/123"
```

Bindings resolve only in functions at runtime — never during the build, and
never in middleware.

## Deploying notes and troubleshooting

- **`DisallowedHost` / `400` on a custom domain** — add the domain to
  `ALLOWED_HOSTS` and its `https://` origin to `CSRF_TRUSTED_ORIGINS`.
- **`ImproperlyConfigured: DJANGO_SECRET_KEY is not set`** — the build succeeds
  without this variable but requests fail: add it in Vercel project settings
  (all environments you deploy) and redeploy. The check is deliberately
  deferred from settings import to request time; see
  [How the deployment is wired](#how-the-deployment-is-wired).
- **CSRF verification failed** — the origin is missing from
  `CSRF_TRUSTED_ORIGINS`, or requests are reaching Django over plain HTTP.
  Vercel terminates TLS and the app trusts `X-Forwarded-Proto`.
- **Database connection errors** — confirm `DATABASE_URL` is present in the
  environment you are viewing (Production vs Preview) and includes
  `?sslmode=require` when the provider requires TLS.
- **Latency in India** — change the function region in
  **Project Settings → Functions** to a region close to your users and to the
  database.
- **Static assets look unstyled** — `STATIC_ROOT` must stay defined so Vercel
  runs `collectstatic`; re-run a deployment after changing CSS.
