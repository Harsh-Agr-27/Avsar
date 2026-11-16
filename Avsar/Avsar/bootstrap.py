"""Startup hook that keeps a serverless deployment usable.

Vercel Functions have no release phase, so there is nowhere to run
``manage.py migrate`` outside of a request. On the first invocation of each
function instance this module applies migrations (which also seeds the
opportunity catalogue) before the request is served.

Deployments with a real database can opt out with ``AUTO_MIGRATE=false`` and run
``python manage.py migrate`` from CI or from a developer machine instead.
"""

import logging
import os

logger = logging.getLogger(__name__)

# Arbitrary constant used to serialise migrations across function instances.
# Postgres advisory locks are per-database and released with the session.
_MIGRATION_LOCK_ID = 7_289_431_065_412

_state = {'checked': False}


def _auto_migrate_enabled():
    return os.environ.get('AUTO_MIGRATE', 'true').strip().lower() not in {
        '0',
        'false',
        'no',
        'off',
    }


def _migrate():
    from django.core.management import call_command

    verbosity = int(os.environ.get('AUTO_MIGRATE_VERBOSITY', '0'))
    call_command('migrate', interactive=False, verbosity=verbosity)


def ensure_database_ready():
    """Apply migrations once per process, never raising into the request."""
    if _state['checked']:
        return
    _state['checked'] = True

    if not _auto_migrate_enabled():
        logger.info('AUTO_MIGRATE is disabled; skipping startup migrations.')
        return

    from django.db import connections

    connection = connections['default']
    is_postgres = connection.vendor == 'postgresql'

    try:
        if is_postgres:
            # Concurrent cold starts would otherwise race on DDL statements.
            with connection.cursor() as cursor:
                cursor.execute('SELECT pg_advisory_lock(%s)', [_MIGRATION_LOCK_ID])
            try:
                _migrate()
            finally:
                with connection.cursor() as cursor:
                    cursor.execute(
                        'SELECT pg_advisory_unlock(%s)', [_MIGRATION_LOCK_ID]
                    )
        else:
            _migrate()
    except Exception:
        logger.exception(
            'Automatic database migration failed. The application will keep '
            'running; run "python manage.py migrate" against this database and '
            'redeploy, or set AUTO_MIGRATE=false to skip this step.'
        )
    else:
        logger.info('Database migrations are up to date.')
