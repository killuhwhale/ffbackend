# Generated by Django 4.0.6 on 2023-05-23 05:35

from django.db import migrations


class Migration(migrations.Migration):
    sql = """
        CREATE OR REPLACE FUNCTION check_completed_workoutgroups_count()
        RETURNS TRIGGER  AS $$
        DECLARE
            row_count INTEGER;
        BEGIN
            -- Check the count of rows with the given owner_id in the table
            -- ARGS (TG_ARGV): max_rows, table_name


            EXECUTE format('SELECT COUNT(*) FROM %s WHERE for_date = ''%s'' and user_id = %s::varchar',TG_ARGV[1], NEW.for_date::date, NEW.user_id)
            INTO row_count;


            IF row_count >= TG_ARGV[0]::integer THEN
                RAISE EXCEPTION 'Too many rows found for Completed WorkoutGroup owner:%s  in table %s', NEW.user_id, TG_ARGV[1];
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """


    dependencies = [
        ('gyms', '0009_func_limit_workout_group_daily'),
    ]

    operations = [
        migrations.RunSQL(sql),
    ]