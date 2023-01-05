Superuser: admin / mostdope

psql -U gym_admin instafit_master
sudo -u postgres psql -U gym_admin -d instafit_master -h 127.0.0.1


AttributeError: Manager isn't available; 'auth.User' has been swapped for 'users.User'
hon begi

echo "515.86.01-0ubuntu0.20.04.1 hold" | sudo dpkg --set-selections


./manage.py shell < myscript.py


Git
Update staging from main
*main
git merge origin/staging
git branch -M staging
git push origin HEAD


Reset DB:

# Delete migration files
find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
find . -path "*/migrations/*.pyc" -delete

# Drop tables
DO $$ DECLARE
      r RECORD;
      BEGIN
        FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = current_schema()) LOOP
            EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
        END LOOP;
      END $$;


Required Features:
    √ iOs and Android
    API work
        √ Intensity and rest per exercise
            - Recording add fields to workou
        √ Many exercises w/ desc and media
        √ Body measurement tracking
        ø Import export data - Future feature.....

    Frontend Work
        ø Fluid data entry
        ø Plate calculator
        ø Taget intensity/ wt based on 1RM calculations
        ø Prefill user's weights based on previous entries




TODO
- Add error for image size erros
    - Curerntly limited to 5MB
    - Error is:
        - error cannot pickle '_io.BufferedRandom' object


Apple watch integrations?

Names
Fitness Platform
    - Fitform

