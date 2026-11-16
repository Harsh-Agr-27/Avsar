from django.db import migrations


def create_catalogue_when_missing(apps, schema_editor):
    opportunity_model = apps.get_model('pages', 'Opportunity')
    table_name = opportunity_model._meta.db_table
    existing_tables = schema_editor.connection.introspection.table_names()
    if table_name not in existing_tables:
        schema_editor.create_model(opportunity_model)


class Migration(migrations.Migration):

    dependencies = [
        ('pages', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(
            create_catalogue_when_missing,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
