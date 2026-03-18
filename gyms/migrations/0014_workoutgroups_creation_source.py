from django.db import migrations, models


def backfill_creation_source(apps, schema_editor):
    WorkoutGroups = apps.get_model("gyms", "WorkoutGroups")
    WorkoutGroups.objects.filter(is_template=True).update(creation_source="template")
    WorkoutGroups.objects.exclude(is_template=True).update(creation_source="manual")


class Migration(migrations.Migration):

    dependencies = [
        ("gyms", "0013_tokenquota_add_total_tokens_used"),
    ]

    operations = [
        migrations.AddField(
            model_name="workoutgroups",
            name="creation_source",
            field=models.CharField(
                choices=[("manual", "Manual"), ("template", "Template"), ("ai", "AI")],
                default="manual",
                max_length=20,
            ),
        ),
        migrations.RunPython(backfill_creation_source, migrations.RunPython.noop),
    ]
