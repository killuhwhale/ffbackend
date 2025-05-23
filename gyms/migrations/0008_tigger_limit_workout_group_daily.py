# Generated by Django 4.0.6 on 2023-04-12 01:54

from django.db import migrations


class Migration(migrations.Migration):
    sql = """
        CREATE OR REPLACE FUNCTION check_workoutgroups_count()
        RETURNS TRIGGER  AS $$
        DECLARE
            row_count INTEGER;
        BEGIN
            -- Check the count of rows with the given owner_id in the table
            -- ARGS (TG_ARGV): max_rows, table_name


            EXECUTE format('SELECT COUNT(*) FROM %s WHERE archived=''f'' and date = ''%s'' and owned_by_class = ''%s'' and owner_id = %s::varchar',TG_ARGV[1], NEW.for_date::date, NEW.owned_by_class, NEW.owner_id)
            INTO row_count;


            IF row_count >= TG_ARGV[0]::integer THEN
                RAISE EXCEPTION 'Too many rows found for WorkoutGroup owner:%s owned_by_class:%s in table %s', NEW.owner_id, NEW.owned_by_class, TG_ARGV[1];
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """
    dependencies = [
        ('gyms', '0007_trigger_gymclasses'),
    ]

    operations = [
        migrations.RunSQL(sql),
    ]
