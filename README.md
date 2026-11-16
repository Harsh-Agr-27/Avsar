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
| `DJANGO_SECRET_KEY` | **Yes** on Vercel | The deploy fails with a clear error if it is missing. Generate with `python -c "import secrets; print(secrets.token_urlsafe(50))"`. |
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
deploys. No framework, build, or output settings are needed: Vercel detects
`Avsar/manage.py`, installs the root `requirements.txt`, runs
`collectstatic`, and routes every request to the WSGI app
(`Avsar/Avsar/wsgi.py`).

Add `DJANGO_SECRET_KEY` before the first deployment (or immediately after, then
redeploy) so the build can load settings.

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

## How the deployment is wired

| Concern | Where it lives |
| --- | --- |
| Function config (`maxDuration`) | [`vercel.json`](vercel.json) |
| Python version (3.12) | [`.python-version`](.python-version) |
| Dependencies installed by Vercel | [`requirements.txt`](requirements.txt) (root) |
| Entrypoint | `Avsar/Avsar/wsgi.py` (detected via `Avsar/manage.py`) |
| Startup migrations + catalogue seed | `Avsar/Avsar/bootstrap.py`, `Avsar/pages/migrations/0003_*` |
| Static files (`/static/`) | `collectstatic` → Vercel CDN, enabled by `STATIC_ROOT` |
| Secrets and `.sqlite3` files | [`.vercelignore`](.vercelignore) |

## Deploying notes and troubleshooting

- **`DisallowedHost` / `400` on a custom domain** — add the domain to
  `ALLOWED_HOSTS` and its `https://` origin to `CSRF_TRUSTED_ORIGINS`.
- **`ImproperlyConfigured: DJANGO_SECRET_KEY is not set`** — add the variable in
  Vercel project settings (all environments you deploy) and redeploy.
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
