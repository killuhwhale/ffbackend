from datetime import timedelta
from django.db import models

from django.contrib.postgres.indexes import GinIndex
from django.utils import timezone




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
    caption = models.CharField(max_length=280)
    media_ids = models.CharField(max_length=1000, default='[]')  # json
    date = models.DateTimeField(auto_now_add=True)
    archived = models.BooleanField(default=False)
    date_archived = models.DateTimeField(blank=True, null=True)
    # -- Todo restrict by day, time doesnt matter.... target_date -> day the wor

    class Meta:
        unique_together = [["owner_id", "owned_by_class", "title"]]
        indexes = [
            GinIndex(fields=['title'], name='workoutgroup_title_trgm', opclasses=['gin_trgm_ops']),
        ]


class Workouts(models.Model):
    group = models.ForeignKey(WorkoutGroups, on_delete=models.CASCADE)
    title = models.CharField(max_length=50, null=False, blank=False)
    desc = models.CharField(max_length=280)
    # Schemas: Round, Rep, Weightlifting
    scheme_type = models.IntegerField(default=0)  # 0, 1, 2
    scheme_rounds = models.CharField(
        max_length=100, default="[]")  # Json stringified list [] rounds/ rep-scheme (not used in weightlifting scheme)
    instruction =  models.CharField(max_length=500, default="")
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['group', 'title']]


class TokenQuota(models.Model):
    user_id = models.CharField(max_length=100, blank=False, null=False, unique=True)
    remaining_tokens = models.PositiveIntegerField(default=1_000_000)
    reset_at = models.DateTimeField(default=timezone.now)

    def reset_if_expired(self):
        if timezone.now() >= self.reset_at:
            self.remaining_tokens = 1_000_000
            self.reset_at = timezone.now() + timedelta(days=30)
            self.save()

    def use_tokens(self, amount: int) -> bool:
        self.reset_if_expired()
        if self.remaining_tokens < amount:
            return False
        self.remaining_tokens -= amount
        self.save()
        return True

    def __str__(self):
        return f"{self.user_id}: {self.remaining_tokens} tokens (resets {self.reset_at})"




class WorkoutStats(models.Model):
    workout = models.OneToOneField(
        Workouts,  # ensure you reference your Workouts model appropriately
        on_delete=models.CASCADE,
        related_name='stats'
    )
    # JSONField for storing tags (e.g., "Core", "Running", "Squat")
    tags = models.JSONField(default=dict)
    # JSONField for storing per-exercise calculated statistics
    items = models.JSONField(default=dict)

    def __str__(self):
        return f"Stats for Workout {self.workout.id}"

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


class WorkoutDualItems(models.Model):
    workout = models.ForeignKey(Workouts, on_delete=models.CASCADE)
    name = models.ForeignKey(
        WorkoutNames, on_delete=models.CASCADE)                # Squat
    ssid = models.IntegerField(default=-1, blank=True) # superset id, groups items together
    constant = models.BooleanField(default=False, blank=True) # For Reps based workout, quantity can be constant

    finished = models.BooleanField(default=False)  # Indicate if the user needs to record their workout still
    penalty = models.CharField(max_length=140, default="") # Store what the penalty is: every x METRIC[reps, distance, duration]

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

    # Record
    r_sets = models.IntegerField(default=0)
    r_reps = models.CharField(max_length=140, default="[0]")
    r_pause_duration = models.FloatField(default=0.00)
    r_duration = models.CharField(max_length=140, default="[0]")
    r_duration_unit = models.IntegerField(default=0)
    r_distance = models.CharField(max_length=140, default="[0]")
    r_distance_unit = models.IntegerField(default=0)
    r_weights = models.CharField(max_length=400, default="[]")
    r_weight_unit = models.CharField(max_length=2, default='kg')
    r_rest_duration = models.FloatField(default=0.0)
    r_rest_duration_unit = models.IntegerField(default=0)
    r_percent_of = models.CharField(max_length=20, default='')


# Currently we are not doing this....
# A completed workout group is to track when a user completes a workout from another source...
class CompletedWorkoutGroups(models.Model):
    # If workout_Group get deleted, we need the title.....
    workout_group = models.ForeignKey(
        WorkoutGroups, on_delete=models.DO_NOTHING)
    user_id = models.CharField(max_length=100)
    title = models.CharField(max_length=50)
    caption = models.CharField(max_length=280)
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
    desc = models.CharField(max_length=280)  # duplicated from OG
    # Schemas: Round, Rep, Weightlifting
    scheme_type = models.IntegerField(default=0)  # duplicated from OG
    scheme_rounds = models.CharField(
        max_length=100, default="[]")  # duplicated from OG
    instruction =  models.CharField(max_length=500, default="")
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


class CompletedWorkoutDualItems(models.Model):
    completed_workout = models.ForeignKey(CompletedWorkouts, on_delete=models.CASCADE)
    user_id = models.CharField(max_length=100)
    name = models.ForeignKey(
        WorkoutNames, on_delete=models.CASCADE)                # Squat
    ssid = models.IntegerField(default=-1, blank=True) # superset id, groups items together
    constant = models.BooleanField(default=False, blank=True) # For Reps based workout, quantity can be constant

    finished = models.BooleanField(default=False)  # Indicate if the user needs to record their workout still
    penalty = models.CharField(max_length=140, default="") # Store what the penalty is: every x METRIC[reps, distance, duration]

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

    # Record
    r_sets = models.IntegerField(default=0)
    r_reps = models.CharField(max_length=140, default="[0]")
    r_pause_duration = models.FloatField(default=0.00)
    r_duration = models.CharField(max_length=140, default="[0]")
    r_duration_unit = models.IntegerField(default=0)
    r_distance = models.CharField(max_length=140, default="[0]")
    r_distance_unit = models.IntegerField(default=0)
    r_weights = models.CharField(max_length=400, default="[]")
    r_weight_unit = models.CharField(max_length=2, default='kg')
    r_rest_duration = models.FloatField(default=0.0)
    r_rest_duration_unit = models.IntegerField(default=0)
    r_percent_of = models.CharField(max_length=20, default='')




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



# Current max/total for a workout item per user
class UserWorkoutMax(models.Model):
    user_id = models.CharField(max_length=200)
    workout_name = models.ForeignKey(WorkoutNames, on_delete=models.CASCADE, related_name='user_maxes')

    # The current max/total value for this workout item
    max_value = models.FloatField()
    unit = models.CharField(max_length=10, default='kg')

    # When this max was last updated
    last_updated = models.DateTimeField(auto_now=True)

    # Optional notes about this max (e.g., "PR at competition")
    notes = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        # Ensure each user can only have one current max per workout item
        unique_together = ('user_id', 'workout_name')

    def __str__(self):
        return f"{self.user_id} - {self.workout_name.name} Max: {self.max_value} {self.unit}"


# History log for tracking changes to maxes over time
class UserWorkoutMaxHistory(models.Model):
    user_id = models.CharField(max_length=200)
    workout_name = models.ForeignKey(WorkoutNames, on_delete=models.CASCADE, related_name='max_history')

    # The recorded max value
    max_value = models.FloatField()
    unit = models.CharField(max_length=10, default='kg')

    # When this max was recorded (unlike UserWorkoutMax, we don't use auto_now because we want to preserve the exact timestamp)
    recorded_date = models.DateTimeField(auto_now_add=True)

    # Optional notes about this max
    notes = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.user_id} - {self.workout_name.name} Max: {self.max_value} {self.unit} on {self.recorded_date.strftime('%Y-%m-%d')}"


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
