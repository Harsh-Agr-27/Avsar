"""
ASGI config for Avsar project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.1/howto/deployment/asgi/
"""

import os
import sys

# Make the ``Avsar`` settings package importable no matter how the serverless
# runtime loads this file (by module name or by path).
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Avsar.settings')

from django.core.asgi import get_asgi_application

from Avsar.bootstrap import require_secret_key

# See Avsar/wsgi.py: the build imports settings without secrets, a running
# deployment must not.
require_secret_key()

application = get_asgi_application()
