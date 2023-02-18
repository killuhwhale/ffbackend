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
    '''
        Look into Middleware
            - request.path is quite generic, might need to be more specfic on /users/
            - Getting user information should only be done by auth user...

    '''


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

    # Completed WorkoutGroup ✅
        - Protect create
            - Test in WorkoutGroup: Protect Completeing WorkoutGroup
        - Protect delete
            - Only User can delete their own completed workout Group

    # Workouts ✅
        - Delete only when workout it belongs to is unfinished
        - Protect create
            - Cannot create Workouts for the wrong WorkoutGroup or User

    # Completed Workouts ✅
        - Protect Delete
            - Ensure user cannot rm another user's Completed Workout.
        - Create, Update, Blocked
            - A completed workout should be a part of the CompletedWorkoutGroup


    # WorkoutItems ✅
        - Create blocked for single items.
        - Delete only when Workout is deleted.
            - Block direct single deletes

    # Completed WorkoutItems ✅
        - No viewset for this.

    # WorkoutNames ✅
        - API to delete only for SuperUser
        - API to create only for SuperUser

    # Favorites ✅
        - Only favorite/ unfavorited with requesting user.
            - protected by auth


    # Users
        - Users should not be able to modify other users
        - reset code
            - rate klimit
            - protect endpoint from wasting my email credits
                - Add special header from inside app


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



Endpoints

/^users/$ []
/^users\.(?P<format>[a-z0-9]+)/?$ []
/^users/profile_image/$ []
/^users/profile_image\.(?P<format>[a-z0-9]+)/?$ []
/^users/update_username/$ []
/^users/update_username\.(?P<format>[a-z0-9]+)/?$ []
/^users/user_info/$ []
/^users/user_info\.(?P<format>[a-z0-9]+)/?$ []
/^users/(?P<pk>[^/.]+)/$ []
/^users/(?P<pk>[^/.]+)\.(?P<format>[a-z0-9]+)/?$ []
/^user/reset_password/$ []
/^user/reset_password\.(?P<format>[a-z0-9]+)/?$ []
/^user/reset_password_with_old/$ []
/^user/reset_password_with_old\.(?P<format>[a-z0-9]+)/?$ []
/^user/send_reset_code/$ []
/^user/send_reset_code\.(?P<format>[a-z0-9]+)/?$ []
/^groups/$ []
/^groups\.(?P<format>[a-z0-9]+)/?$ []
/^groups/(?P<pk>[^/.]+)/$ []
/^groups/(?P<pk>[^/.]+)\.(?P<format>[a-z0-9]+)/?$ []
/^$ [View,as_view,<locals>]
/^\.(?P<format>[a-z0-9]+)/?$ [View,as_view,<locals>]


/^gyms/$ []
/^gyms\.(?P<format>[a-z0-9]+)/?$ []
/^gyms/favorite/$ []
/^gyms/favorite\.(?P<format>[a-z0-9]+)/?$ []
/^gyms/unfavorite/$ []
/^gyms/unfavorite\.(?P<format>[a-z0-9]+)/?$ []
/^gyms/user_gyms/$ []
/^gyms/user_gyms\.(?P<format>[a-z0-9]+)/?$ []
/^gyms/(?P<pk>[^/.]+)/$ []
/^gyms/(?P<pk>[^/.]+)\.(?P<format>[a-z0-9]+)/?$ []
/^gyms/(?P<pk>[^/.]+)/edit_media/$ []
/^gyms/(?P<pk>[^/.]+)/edit_media\.(?P<format>[a-z0-9]+)/?$ []
/^gyms/(?P<pk>[^/.]+)/gymsclasses/$ []
/^gyms/(?P<pk>[^/.]+)/gymsclasses\.(?P<format>[a-z0-9]+)/?$ []
/^gyms/(?P<pk>[^/.]+)/user_favorites/$ []
/^gyms/(?P<pk>[^/.]+)/user_favorites\.(?P<format>[a-z0-9]+)/?$ []
/^gymClasses/$ []
/^gymClasses\.(?P<format>[a-z0-9]+)/?$ []
/^gymClasses/favorite/$ []
/^gymClasses/favorite\.(?P<format>[a-z0-9]+)/?$ []
/^gymClasses/unfavorite/$ []
/^gymClasses/unfavorite\.(?P<format>[a-z0-9]+)/?$ []
/^gymClasses/(?P<pk>[^/.]+)/$ []
/^gymClasses/(?P<pk>[^/.]+)\.(?P<format>[a-z0-9]+)/?$ []
/^gymClasses/(?P<pk>[^/.]+)/edit_media/$ []
/^gymClasses/(?P<pk>[^/.]+)/edit_media\.(?P<format>[a-z0-9]+)/?$ []
/^gymClasses/(?P<pk>[^/.]+)/user_favorites/$ []
/^gymClasses/(?P<pk>[^/.]+)/user_favorites\.(?P<format>[a-z0-9]+)/?$ []
/^gymClasses/(?P<pk>[^/.]+)/workouts/$ []
/^gymClasses/(?P<pk>[^/.]+)/workouts\.(?P<format>[a-z0-9]+)/?$ []
/^workoutGroups/$ []
/^workoutGroups\.(?P<format>[a-z0-9]+)/?$ []
/^workoutGroups/favorite/$ []
/^workoutGroups/favorite\.(?P<format>[a-z0-9]+)/?$ []
/^workoutGroups/finish/$ []
/^workoutGroups/finish\.(?P<format>[a-z0-9]+)/?$ []
/^workoutGroups/unfavorite/$ []
/^workoutGroups/unfavorite\.(?P<format>[a-z0-9]+)/?$ []
/^workoutGroups/(?P<pk>[^/.]+)/$ []
/^workoutGroups/(?P<pk>[^/.]+)\.(?P<format>[a-z0-9]+)/?$ []
/^workoutGroups/(?P<pk>[^/.]+)/add_media_to_workout/$ []
/^workoutGroups/(?P<pk>[^/.]+)/add_media_to_workout\.(?P<format>[a-z0-9]+)/?$ []
/^workoutGroups/(?P<pk>[^/.]+)/class_workouts/$ []
/^workoutGroups/(?P<pk>[^/.]+)/class_workouts\.(?P<format>[a-z0-9]+)/?$ []
/^workoutGroups/(?P<pk>[^/.]+)/remove_media_from_workout/$ []
/^workoutGroups/(?P<pk>[^/.]+)/remove_media_from_workout\.(?P<format>[a-z0-9]+)/?$ []
/^workoutGroups/(?P<pk>[^/.]+)/user_workouts/$ []
/^workoutGroups/(?P<pk>[^/.]+)/user_workouts\.(?P<format>[a-z0-9]+)/?$ []
/^workouts/$ []
/^workouts\.(?P<format>[a-z0-9]+)/?$ []
/^workouts/(?P<pk>[^/.]+)/$ []
/^workouts/(?P<pk>[^/.]+)\.(?P<format>[a-z0-9]+)/?$ []
/^workoutNames/$ []
/^workoutNames\.(?P<format>[a-z0-9]+)/?$ []
/^workoutNames/(?P<pk>[^/.]+)/$ []
/^workoutNames/(?P<pk>[^/.]+)\.(?P<format>[a-z0-9]+)/?$ []
/^workoutNames/(?P<pk>[^/.]+)/add_media_to_workout_name/$ []
/^workoutNames/(?P<pk>[^/.]+)/add_media_to_workout_name\.(?P<format>[a-z0-9]+)/?$ []
/^workoutNames/(?P<pk>[^/.]+)/remove_media_from_workout_name/$ []
/^workoutNames/(?P<pk>[^/.]+)/remove_media_from_workout_name\.(?P<format>[a-z0-9]+)/?$ []
/^workoutCategories/$ []
/^workoutCategories\.(?P<format>[a-z0-9]+)/?$ []
/^workoutCategories/(?P<pk>[^/.]+)/$ []
/^workoutCategories/(?P<pk>[^/.]+)\.(?P<format>[a-z0-9]+)/?$ []
/^workoutItems/$ []
/^workoutItems\.(?P<format>[a-z0-9]+)/?$ []
/^workoutItems/items/$ []
/^workoutItems/items\.(?P<format>[a-z0-9]+)/?$ []
/^workoutItems/(?P<pk>[^/.]+)/$ []
/^workoutItems/(?P<pk>[^/.]+)\.(?P<format>[a-z0-9]+)/?$ []
/^completedWorkoutGroups/$ []
/^completedWorkoutGroups\.(?P<format>[a-z0-9]+)/?$ []
/^completedWorkoutGroups/workouts/$ []
/^completedWorkoutGroups/workouts\.(?P<format>[a-z0-9]+)/?$ []
/^completedWorkoutGroups/(?P<pk>[^/.]+)/$ []
/^completedWorkoutGroups/(?P<pk>[^/.]+)\.(?P<format>[a-z0-9]+)/?$ []
/^completedWorkoutGroups/(?P<pk>[^/.]+)/add_media_to_workout/$ []
/^completedWorkoutGroups/(?P<pk>[^/.]+)/add_media_to_workout\.(?P<format>[a-z0-9]+)/?$ []
/^completedWorkoutGroups/(?P<pk>[^/.]+)/completed_workout_group/$ []
/^completedWorkoutGroups/(?P<pk>[^/.]+)/completed_workout_group\.(?P<format>[a-z0-9]+)/?$ []
/^completedWorkoutGroups/(?P<pk>[^/.]+)/completed_workout_group_by_og_workout_group/$ []
/^completedWorkoutGroups/(?P<pk>[^/.]+)/completed_workout_group_by_og_workout_group\.(?P<format>[a-z0-9]+)/?$ []
/^completedWorkoutGroups/(?P<pk>[^/.]+)/remove_media_from_workout/$ []
/^completedWorkoutGroups/(?P<pk>[^/.]+)/remove_media_from_workout\.(?P<format>[a-z0-9]+)/?$ []
/^completedWorkouts/$ []
/^completedWorkouts\.(?P<format>[a-z0-9]+)/?$ []
/^completedWorkouts/(?P<pk>[^/.]+)/$ []
/^completedWorkouts/(?P<pk>[^/.]+)\.(?P<format>[a-z0-9]+)/?$ []
/^coaches/$ []
/^coaches\.(?P<format>[a-z0-9]+)/?$ []
/^coaches/remove/$ []
/^coaches/remove\.(?P<format>[a-z0-9]+)/?$ []
/^coaches/(?P<pk>[^/.]+)/$ []
/^coaches/(?P<pk>[^/.]+)\.(?P<format>[a-z0-9]+)/?$ []
/^coaches/(?P<pk>[^/.]+)/coaches/$ []
/^coaches/(?P<pk>[^/.]+)/coaches\.(?P<format>[a-z0-9]+)/?$ []
/^classMembers/$ []
/^classMembers\.(?P<format>[a-z0-9]+)/?$ []
/^classMembers/remove/$ []
/^classMembers/remove\.(?P<format>[a-z0-9]+)/?$ []
/^classMembers/(?P<pk>[^/.]+)/$ []
/^classMembers/(?P<pk>[^/.]+)\.(?P<format>[a-z0-9]+)/?$ []
/^classMembers/(?P<pk>[^/.]+)/members/$ []
/^classMembers/(?P<pk>[^/.]+)/members\.(?P<format>[a-z0-9]+)/?$ []
/^profile/gym_class_favs/$ []
/^profile/gym_class_favs\.(?P<format>[a-z0-9]+)/?$ []
/^profile/gym_favs/$ []
/^profile/gym_favs\.(?P<format>[a-z0-9]+)/?$ []
/^profile/profile/$ []
/^profile/profile\.(?P<format>[a-z0-9]+)/?$ []
/^profile/workout_groups/$ []
/^profile/workout_groups\.(?P<format>[a-z0-9]+)/?$ []
/^stats/(?P<pk>[^/.]+)/user_workouts/$ []
/^stats/(?P<pk>[^/.]+)/user_workouts\.(?P<format>[a-z0-9]+)/?$ []
