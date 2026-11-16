"""
WSGI config for Avsar project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.1/howto/deployment/wsgi/
"""

import os
import sys

# Make the ``Avsar`` settings package importable no matter how the serverless
# runtime loads this file (by module name or by path).
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Avsar.settings')

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()

# Vercel Functions have no release phase; keep the schema in sync on cold start.
from Avsar.bootstrap import ensure_database_ready

ensure_database_ready()

# Some WSGI hosts look for ``app`` instead of ``application``.
app = application
