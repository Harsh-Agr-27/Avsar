"""Seed the opportunity catalogue that ships with Avsar.

``pages/fixtures/opportunities.json`` holds the curated catalogue so a freshly
provisioned database (for example the Postgres database behind a Vercel
deployment) is not empty. The migration is safe to re-run: it does nothing when
rows already exist, and ignores rows whose primary key is already present.
"""

import json
from pathlib import Path

from django.db import migrations

FIXTURE_PATH = Path(__file__).resolve().parent.parent / 'fixtures' / 'opportunities.json'

FIELDS = (
    'id',
    'opportunity_type',
    'title',
    'provider',
    'image',
    'benefit',
    'deadline',
    'verified',
    'mode',
    'min_education',
    'min_marks',
    'max_income',
    'category',
    'gender',
    'state',
    'min_age',
    'max_age',
    'pwd_only',
    'skills',
    'description',
    'eligibility',
    'documents',
    'official_link',
)


def seed_opportunities(apps, schema_editor):
    opportunity_model = apps.get_model('pages', 'Opportunity')
    database = schema_editor.connection.alias

    if opportunity_model.objects.using(database).exists():
        return
    if not FIXTURE_PATH.exists():
        return

    records = json.loads(FIXTURE_PATH.read_text(encoding='utf-8'))
    opportunity_model.objects.using(database).bulk_create(
        [
            opportunity_model(**{field: record.get(field) for field in FIELDS})
            for record in records
        ],
        ignore_conflicts=True,
    )


class Migration(migrations.Migration):

    dependencies = [
        ('pages', '0002_ensure_opportunity_catalogue'),
    ]

    operations = [
        migrations.RunPython(
            seed_opportunities,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
