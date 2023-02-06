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


# Testing
    # Gyms ✅
        - Protect delete
    # Gym Classes ✅
        - Protect delete
        - Protect create w/ gym

    # Coaches ✅
        - Protect create/delete
            - Only gym owners can create coaches for a class

    # Members ✅
        - Protect create/delete
            - Only gym owners or coaches can create members for a class


    # WorkoutGroup ✅
        - Protect create w/ ownerid
        - Protect Delete, ensure archive
        - Protect Finishing Empty Workout
        - Protect Completeing WorkoutGroup
            - Compelte is just creating a CompleteWorkoutGroup

    # Completed WorkoutGroup
        - Protect create ✅
        - Protect delete
            - Only User can delete their own completed workout Group

    # Workouts ✅
        - Delete only when workout it belongs to is unfinished
        - Protect create
            - Cannot create Workouts for the wrong WorkoutGroup or User

    # Completed Workouts
        - Should not have an API to delete

    # WorkoutItems
        - Delete only when workout->WorkoutGroup it belongs to is unfinished

    # Completed WorkoutItems
        - Should not have an API to delete

    # WorkoutNames ✅
        - API to delete only for SuperUser
        - API to create only for SuperUser

    # Users
        - Users should not be able to modify other users



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

