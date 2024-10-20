# Generated by Django 4.0.6 on 2023-04-10 01:25

from django.db import migrations


class Migration(migrations.Migration):
    sql = """
      CREATE TRIGGER check_count_gymclasses
                BEFORE INSERT ON gyms_gymclasses
                FOR EACH ROW
                WHEN (NEW.gym_id IS NOT NULL)
                EXECUTE FUNCTION check_gymclasses_count('15', 'gyms_gymclasses');
    """
    dependencies = [
        ('gyms', '0006_func_gymclasses'),
    ]

    operations = [
        migrations.RunSQL(sql),
    ]
