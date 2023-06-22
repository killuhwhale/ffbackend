from django.db import models
from django.core.exceptions import ValidationError
from functools import wraps



class Gyms(models.Model):
    title = models.CharField(max_length=50)
    desc = models.CharField(max_length=1000)
    owner_id = models.CharField(max_length=100)
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [["title", "owner_id"]]




class GymClasses(models.Model):
    gym = models.ForeignKey(Gyms, on_delete=models.CASCADE)
    title = models.CharField(max_length=50)
    private = models.BooleanField(default=False)
    desc = models.CharField(max_length=1000)
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [["title", "gym"]]


class Coaches(models.Model):
    user_id = models.CharField(max_length=100)
    gym_class = models.ForeignKey(GymClasses, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [["user_id", "gym_class"]]


class ClassMembers(models.Model):
    user_id = models.CharField(max_length=100)
    gym_class = models.ForeignKey(GymClasses, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [["user_id", "gym_class"]]


class GymClassFavorites(models.Model):
    user_id = models.CharField(max_length=100)
    gym_class = models.ForeignKey(GymClasses, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [["user_id", "gym_class"]]


class GymFavorites(models.Model):
    user_id = models.CharField(max_length=100)
    gym = models.ForeignKey(Gyms, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [["user_id", "gym"]]


# Represents a Grouped Workout/ Media Post, allows to create multiple Workouts
class WorkoutGroups(models.Model):
    owner_id = models.CharField(
        max_length=100, blank=False, null=False)  # Class ID or USER ID
    owned_by_class = models.BooleanField(default=True)
    # Allows Workouts to be added to Group when false
    finished = models.BooleanField(default=False)
    for_date = models.DateTimeField()  # Date the Workout is intended for
    title = models.CharField(max_length=50, blank=False, null=False)
    caption = models.CharField(max_length=250)
    media_ids = models.CharField(max_length=1000, default='[]')  # json
    date = models.DateTimeField(auto_now_add=True)
    archived = models.BooleanField(default=False)
    date_archived = models.DateTimeField(blank=True, null=True)
    # -- Todo restrict by day, time doesnt matter.... target_date -> day the wor

    class Meta:
        unique_together = [["owner_id", "owned_by_class", "title"]]


class Workouts(models.Model):
    group = models.ForeignKey(WorkoutGroups, on_delete=models.CASCADE)
    title = models.CharField(max_length=50, null=False, blank=False)
    desc = models.CharField(max_length=250)
    # Schemas: Round, Rep, Weightlifting
    scheme_type = models.IntegerField(default=0)  # 0, 1, 2
    scheme_rounds = models.CharField(
        max_length=100, default="[]")  # Json stringified list [] rounds/ rep-scheme (not used in weightlifting scheme)
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['group', 'title']]


class WorkoutCategories(models.Model):
    title = models.CharField(max_length=100, unique=True)


class WorkoutNames(models.Model):
    name = models.CharField(max_length=100, unique=True)
    desc = models.CharField(max_length=3000)
    media_ids = models.CharField(max_length=1000, default='[]')  # json
    date = models.DateTimeField(auto_now_add=True)
    categories = models.ManyToManyField(WorkoutCategories)
    primary = models.ForeignKey(
        WorkoutCategories, related_name="workoutcategories_primary_set", on_delete=models.CASCADE, blank=True, null=True)
    secondary = models.ForeignKey(
        WorkoutCategories, related_name="workoutcategories_secondary_set", on_delete=models.CASCADE, blank=True, null=True)


class WorkoutItems(models.Model):
    workout = models.ForeignKey(Workouts, on_delete=models.CASCADE)
    name = models.ForeignKey(
        WorkoutNames, on_delete=models.CASCADE)                # Squat
    ssid = models.IntegerField(default=-1, blank=True) # superset id, groups items together
    constant = models.BooleanField(default=False, blank=True) # For Reps based workout, quantity can be constant
    # removed:   intensity, rounds
    sets = models.IntegerField(default=0)
    reps = models.CharField(max_length=140, default="[0]")
    pause_duration = models.FloatField(default=0.00)
    duration = models.CharField(max_length=140, default="[0]")
    duration_unit = models.IntegerField(default=0)
    distance = models.CharField(max_length=140, default="[0]")
    distance_unit = models.IntegerField(default=0)
    weights = models.CharField(
        max_length=400, default="[]")
    weight_unit = models.CharField(max_length=2, default='kg')
    rest_duration = models.FloatField(default=0.0)
    rest_duration_unit = models.IntegerField(default=0)
    percent_of = models.CharField(max_length=20, default='')
    order = models.IntegerField()  # order added by user.
    date = models.DateTimeField(auto_now_add=True)


class CompletedWorkoutGroups(models.Model):
    # If workout_Group get deleted, we need the title.....
    workout_group = models.ForeignKey(
        WorkoutGroups, on_delete=models.DO_NOTHING)
    user_id = models.CharField(max_length=100)
    title = models.CharField(max_length=250)
    caption = models.CharField(max_length=250)
    media_ids = models.CharField(max_length=1000, default='[]')  # json
    date = models.DateTimeField(auto_now_add=True)
    for_date = models.DateTimeField()  # Date the Workout is intended for

    class Meta:
        unique_together = [["workout_group", "user_id"]]


class CompletedWorkouts(models.Model):
    completed_workout_group = models.ForeignKey(
        CompletedWorkoutGroups, on_delete=models.CASCADE)
    workout = models.ForeignKey(Workouts, on_delete=models.CASCADE)
    user_id = models.CharField(max_length=100)
    title = models.CharField(max_length=50)  # duplicated from OG
    desc = models.CharField(max_length=250)  # duplicated from OG
    # Schemas: Round, Rep, Weightlifting
    scheme_type = models.IntegerField(default=0)  # duplicated from OG
    scheme_rounds = models.CharField(
        max_length=100, default="[]")  # duplicated from OG
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [["completed_workout_group", "workout", "user_id"]]


class CompletedWorkoutItems(models.Model):
    user_id = models.CharField(max_length=100)
    completed_workout = models.ForeignKey(
        CompletedWorkouts, on_delete=models.CASCADE)
    name = models.ForeignKey(
        WorkoutNames, on_delete=models.CASCADE)                # Squat
    ssid = models.IntegerField(default=-1, blank=True)
    constant = models.BooleanField(default=False, blank=True) # For Reps based workout, quantity is constant
    # removed:   intensity, rounds
    sets = models.IntegerField(default=0)                      # 3
    reps = models.CharField(max_length=140, default="0")       # 5
    pause_duration = models.FloatField(default=0.00)

    duration = models.CharField(max_length=140, default="0")   # None
    duration_unit = models.IntegerField(default=0)             # None
    distance = models.CharField(max_length=140, default="0")
    distance_unit = models.IntegerField(default=0)
    weights = models.CharField(
        max_length=400, default="[]")   # [100, 155, 185]
    weight_unit = models.CharField(max_length=2, default='kg')  # None
    rest_duration = models.FloatField(default=0.0)                  # None
    rest_duration_unit = models.IntegerField(default=0)             # None
    percent_of = models.CharField(max_length=20, default='1RM')  # None
    order = models.IntegerField()             # None
    date = models.DateTimeField(auto_now_add=True)


class LikedWorkouts(models.Model):
    user_id = models.CharField(max_length=200)
    workout = models.ForeignKey(Workouts, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [["user_id", "workout"]]


class BodyMeasurements(models.Model):
    '''
        bodyweight
        bodyfat
    '''
    user_id = models.CharField(max_length=200)
    bodyweight = models.FloatField(default=0.0)
    bodyweight_unit = models.CharField(max_length=2, default='kg')
    bodyfat = models.FloatField(default=0.0)
    armms = models.FloatField(default=0.0)
    calves = models.FloatField(default=0.0)
    neck = models.FloatField(default=0.0)
    thighs = models.FloatField(default=0.0)
    chest = models.FloatField(default=0.0)
    waist = models.FloatField(default=0.0)
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [["user_id", "date"]]


class ResetPasswords(models.Model):

    email = models.CharField(max_length=75, unique=True)
    code = models.CharField(max_length=12, blank=False)
    expires_at = models.DateTimeField(
        blank=True, null=True)  # Updated on add only


'''


Workout Schemes:
    Round Scheme:
        - Rounds plus a series of workout items

    Rep scheme:
        - Rounds of varying reps of workout items




Weightlift Scheme

Squat 2x5 @ [80%, 85%]
Bench 2x5 @ [80%, 85%]
Curls 8x12 @ [25lb]


Round Scheme
8 rounds (Tabata)
    20sec situps
    10sec rest

5 Rounds:
    20 Sqats
    10 pushups
    400m run
    30sec burpee


Rep Scheme
21-15-9:
   1 HSPU
   1 Deadlifts


'''
