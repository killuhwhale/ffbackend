from datetime import datetime, timedelta
from gyms.models import Gyms, GymClasses, WorkoutGroups, Workouts, WorkoutItems, WorkoutNames, WorkoutCategories, CompletedWorkoutGroups
from django.contrib.auth import get_user_model
import pytz
tz = pytz.timezone("US/Pacific")

'''

./manage.py shell < gyms/create_test_data.py


'''

User =  get_user_model()

user, nc = User.objects.get_or_create(
    email='andayac@gmail.com',
)
if nc:
    user.set_password("123")
    user.save()
# gym, nc = Gyms.objects.get_or_create(
#     title= "Nc Fitter",
#     desc= "abcdefghj",
#     owner_id= "1",
# )

# print(gym.title, user.email)

# gym_class, nc = GymClasses.objects.get_or_create(
#     title= "Nc Fitter Class",
#     desc= "Testing",
#     gym= gym,
# )
# workout_group, nc = WorkoutGroups.objects.get_or_create(
#     owner_id= gym_class.id,
#     owned_by_class= True,
#     finished= True,
#     # for_date= datetime.today(),
#     title= "NcFirsFittertWorkout",
#     caption= 'Testing',
# )

# workout, nc = Workouts.objects.get_or_create(
#     group= workout_group,
#     title= "Regular globo gym",
#     desc= "testing wod",
#     scheme_type= 0,
#     # "scheme_rounds": '[]',
# )

# workout_name, nc = WorkoutNames.objects.get_or_create(
#     name= 'Squat',
#     # desc= 'Back squat, if loaded. Parallel.',
#     # categories= [3, 4, 14],
#     # primary_id= 3,
#     # secondary_id= 14,

# )
# workout_item_squat, nc = WorkoutItems.objects.get_or_create(
#     workout= workout,
#     name= workout_name,
#     # ssid= '1',
#     # 'constant': '',
#     sets= '3',
#     reps= '[2]',
#     # 'duration': '[]',
#     # 'duration_unit': '',
#     # 'distance': '[]',
#     # 'distance_unit': '',
#     weights= '[135,150,185] ',
#     weight_unit= 'lb',
#     # 'rest_duration': '',
#     # 'rest_duration_unit': '',
#     # 'percent_of': '',
#     order= 1,
# )


# workout_name, nc = WorkoutNames.objects.get_or_create(
#     name= 'Bench press',
#     # desc= 'Back squat, if loaded. Parallel.',
#     # categories= [3, 4, 14],
#     # primary_id= 3,
#     # secondary_id= 14,

# )
# workout_item_squat, nc = WorkoutItems.objects.get_or_create(
#     workout= workout,
#     name= workout_name,
#     ssid= '1',
#     # 'constant': '',
#     sets= '2',
#     reps= '[4]',
#     # 'duration': '[]',
#     # 'duration_unit': '',
#     # 'distance': '[]',
#     # 'distance_unit': '',
#     weights= '[135,150] ',
#     weight_unit= 'lb',
#     # 'rest_duration': '',
#     # 'rest_duration_unit': '',
#     # 'percent_of': '',
#     order= 2,
# )


# workout_name, nc = WorkoutNames.objects.get_or_create(
#     name= 'Clean',
#     # desc= 'Back squat, if loaded. Parallel.',
#     # categories= [3, 4, 14],
#     # primary_id= 3,
#     # secondary_id= 14,

# )
# workout_item_squat, nc = WorkoutItems.objects.get_or_create(
#     workout= workout,
#     name= workout_name,
#     ssid= '1',
#     # 'constant': '',
#     sets= '3',
#     reps= '[2]',
#     # 'duration': '[]',
#     # 'duration_unit': '',
#     # 'distance': '[]',
#     # 'distance_unit': '',
#     weights= '[135,150, 185] ',
#     weight_unit= 'lb',
#     # 'rest_duration': '',
#     # 'rest_duration_unit': '',
#     # 'percent_of': '',
#     order= 3,
# )


###############################
#
#  Personal Workouts
#
#########################




class WorkoutItem:
    def __init__(self,
        workout=None,
        name=None,
        ssid=None,
        constant=None,
        sets=None,
        reps=None,
        duration=None,
        duration_unit=None,
        distance=None,
        distance_unit=None,
        weights=None,
        weight_unit=None,
        rest_duration=None,
        rest_duration_unit=None,
        percent_of=None,
        order=None,
    ):
        self._args = {
            'workout': workout,
            'name': name,
            'ssid': ssid,
            'constant': constant,
            'sets': sets,
            'reps': reps,
            'duration': duration,
            'duration_unit': duration_unit,
            'distance': distance,
            'distance_unit': distance_unit,
            'weights': weights,
            'weight_unit': weight_unit,
            'rest_duration': rest_duration,
            'rest_duration_unit': rest_duration_unit,
            'percent_of': percent_of,
            'order': order,
        }

    def args(self):
        return {k: v for k,v in self._args.items() if not v is None}

day = 0
def createGroup(title):
    global day
    workout_group, nc = WorkoutGroups.objects.get_or_create(
        owner_id= user.id,
        owned_by_class= False,
        finished= True,
        for_date= tz.localize(datetime.today() + timedelta(days=day)),
        title= title,
        caption= "Test cap",
    )
    day += 1
    return workout_group


def createWorkout(title, workout_group):
    workout, nc = Workouts.objects.get_or_create(
        group= workout_group,
        title= title,
        desc= "test desc",
        scheme_type= 0,
        # "scheme_rounds": '[]',
    )
    return workout


def createWorkoutItem(workout, name, sets, reps, weights, order):
    item, nc = WorkoutItems.objects.get_or_create(**WorkoutItem(
        workout= workout,
        name= name,
        sets= sets,
        reps= str(reps),
        weights= str(weights),
        weight_unit= 'lb',
        order= order,
    ).args())
    return item


def createWorkoutItemWithDuration(workout, name, sets, duration, weights, order):
    item, nc = WorkoutItems.objects.get_or_create(**WorkoutItem(
        workout= workout,
        name= name,
        sets= sets,
        duration=str(duration),
        duration_unit=0,
        weights= str(weights),
        weight_unit= 'lb',
        order= order,
    ).args())
    return item



clean= WorkoutNames.objects.get(
    name= 'Clean',
)
rollsesh= WorkoutNames.objects.get(
    name= 'Rolling Sesh',
)


# Monday
squat= WorkoutNames.objects.get(
    name= 'Squat',
)
legpress= WorkoutNames.objects.get(
    name= 'Leg Press',
)
hammycurl= WorkoutNames.objects.get(
    name= 'Hamstring Curl',
)
planks= WorkoutNames.objects.get(
    name= 'Plank',
)
cs_rows= WorkoutNames.objects.get(
    name= 'Chest Supported Rows',
)




# Tuesday
bench= WorkoutNames.objects.get(
    name= 'Bench Press',
)
db_bench= WorkoutNames.objects.get(
    name= 'Dumbbell Chest Press',
)
db_bentover_row= WorkoutNames.objects.get(
    name= 'Dumbbell Bent Over Row',
)
side_plank= WorkoutNames.objects.get(
    name= 'Side Plank',
)


# Wednesday
hill_sprints= WorkoutNames.objects.get(
    name= 'Hill Sprints',
)


# Thursday
deadlift= WorkoutNames.objects.get(
    name= 'Deadlift',
)
good_morning= WorkoutNames.objects.get(
    name= 'Good Morning',
)
hang_leg_raise= WorkoutNames.objects.get(
    name= 'Hanging Leg Raises',
)
crunches= WorkoutNames.objects.get(
    name= 'Crunch',
)
leg_ext= WorkoutNames.objects.get(
    name= 'Leg Extension',
)

# Friday
should_press= WorkoutNames.objects.get(
    name= 'Shoulder Press',
)
dips= WorkoutNames.objects.get(
    name= 'Dips',
)
chinups= WorkoutNames.objects.get(
    name= 'Chin-Up',
)
landmine= WorkoutNames.objects.get(
    name= 'Landmine',
)


# Saturday
weighted_walk= WorkoutNames.objects.get(
    name= 'Walking',
)







def week531():
    CompletedWorkoutGroups.objects.all().delete()
    WorkoutGroups.objects.all().delete()
    weeks = 4

    s_squat = 185
    s_deadlift = 185
    s_bench = 205
    s_should_press = 95

    reps = [
        [5,5,5],
        [3,3,3],
        [[3,5], [1,3], [1,1]],
        [5,5,5],
    ]

    weights = [
        [.65, .75, .85],
        [.70, .80, .90],
        [.75, .85, .95],
        [.40, .50, .60],
    ]


    for w in range(weeks):
        print("Creating week: ", w)
        # Monday
        g = createGroup(f"monday-{w}")
        wrk = createWorkout(f"workout-{w}", g)
        _reps = reps[w]
        _weights = weights[w]
        if type(_reps[0]) == type([]):
            createWorkoutItem(wrk, squat, _reps[0][0], [_reps[0][1]], [_weights[0] * s_squat], 1)
            createWorkoutItem(wrk, squat, _reps[1][0], [_reps[1][1]], [_weights[1] * s_squat], 2)
            createWorkoutItem(wrk, squat, _reps[2][0], [_reps[2][1]], [_weights[2] * s_squat], 3)
        else:
            createWorkoutItem(wrk, squat, 1, [_reps[0]],  [_weights[0] * s_squat], 1)
            createWorkoutItem(wrk, squat, 1, [_reps[1]],  [_weights[1] * s_squat], 2)
            createWorkoutItem(wrk, squat, 1, [_reps[2]],  [_weights[2] * s_squat], 3)

        legpress_weight = [360]
        hammycurl_weight = [100]
        planks_weight = [25]
        cs_rows_weight = [115]
        # Accessories
        createWorkoutItem(wrk, legpress, 5, [15], legpress_weight, 4)
        createWorkoutItem(wrk, hammycurl, 5, [12], hammycurl_weight, 5)
        createWorkoutItemWithDuration(wrk, planks, 5, [30], planks_weight, 6)
        createWorkoutItem(wrk, cs_rows, 5, [12], cs_rows_weight, 7)


        # Tuesday
        g = createGroup(f"tuesday-{w}")
        wrk = createWorkout(f"workout-{w}", g)
        _reps = reps[w]
        _weights = weights[w]
        if type(_reps[0]) == type([]):
            createWorkoutItem(wrk, bench, _reps[0][0], [_reps[0][1]], [_weights[0] * s_bench], 1)
            createWorkoutItem(wrk, bench, _reps[1][0], [_reps[1][1]], [_weights[1] * s_bench], 2)
            createWorkoutItem(wrk, bench, _reps[2][0], [_reps[2][1]], [_weights[2] * s_bench], 3)
        else:
            createWorkoutItem(wrk, bench, 1, [_reps[0]],  [_weights[0] * s_bench], 1)
            createWorkoutItem(wrk, bench, 1, [_reps[1]],  [_weights[1] * s_bench], 2)
            createWorkoutItem(wrk, bench, 1, [_reps[2]],  [_weights[2] * s_bench], 3)




        db_bench_wt = [50]
        db_bentover_row_wt = [100]
        side_plank_wt = [25]
        # Accessories
        createWorkoutItem(wrk, db_bench, 5, [15], db_bench_wt, 4)
        createWorkoutItem(wrk, db_bentover_row, 5, [10], db_bentover_row_wt, 5)
        createWorkoutItemWithDuration(wrk, side_plank, 5, [30], side_plank_wt, 6)




        # Wednesday
        g = createGroup(f"wednesday-{w}")
        wrk = createWorkout(f"workout-{w}", g)

        createWorkoutItem(wrk, hill_sprints, 3, [10], [], 1)


        # Thursday
        g = createGroup(f"thursday-{w}")
        wrk = createWorkout(f"workout-{w}", g)
        _reps = reps[w]
        _weights = weights[w]
        if type(_reps[0]) == type([]):
            createWorkoutItem(wrk, deadlift, _reps[0][0], _reps[0][1], [_weights[0] * s_deadlift], 1)
            createWorkoutItem(wrk, deadlift, _reps[1][0], _reps[1][1], [_weights[1] * s_deadlift], 2)
            createWorkoutItem(wrk, deadlift, _reps[2][0], _reps[2][1], [_weights[2] * s_deadlift], 3)
        else:
            createWorkoutItem(wrk, deadlift, 1, [_reps[0]],  [_weights[0] * s_deadlift], 1)
            createWorkoutItem(wrk, deadlift, 1, [_reps[1]],  [_weights[1] * s_deadlift], 2)
            createWorkoutItem(wrk, deadlift, 1, [_reps[2]],  [_weights[2] * s_deadlift], 3)

        good_morning_weight = [45]
        hang_leg_raise_weight = [0]
        crunches_weight = [0]
        leg_ext_weight = [80]
        # Accessories
        createWorkoutItem(wrk, good_morning, 5, [12], good_morning_weight, 4)
        createWorkoutItem(wrk, hang_leg_raise, 5, [15], hang_leg_raise_weight, 5)
        createWorkoutItem(wrk, crunches, 5, [20], crunches_weight, 6)
        createWorkoutItem(wrk, leg_ext, 5, [12], leg_ext_weight, 7)


        # Friday
        g = createGroup(f"friday-{w}")
        wrk = createWorkout(f"workout-{w}", g)
        _reps = reps[w]
        _weights = weights[w]
        if type(_reps[0]) == type([]):
            createWorkoutItem(wrk, should_press, _reps[0][0], _reps[0][1], [_weights[0] * s_should_press], 1)
            createWorkoutItem(wrk, should_press, _reps[1][0], _reps[1][1], [_weights[1] * s_should_press], 2)
            createWorkoutItem(wrk, should_press, _reps[2][0], _reps[2][1], [_weights[2] * s_should_press], 3)
        else:
            createWorkoutItem(wrk, should_press, 1, [_reps[0]],  [_weights[0] * s_should_press], 1)
            createWorkoutItem(wrk, should_press, 1, [_reps[1]],  [_weights[1] * s_should_press], 2)
            createWorkoutItem(wrk, should_press, 1, [_reps[2]],  [_weights[2] * s_should_press], 3)


        should_press_weight = [45]
        dips_weight = [0]
        chinups_weight = [0]
        landmine_weight = [80]
        # Accessories
        createWorkoutItem(wrk, should_press, 5, [12], should_press_weight, 4)
        createWorkoutItem(wrk, dips, 5, [15], dips_weight, 5)
        createWorkoutItem(wrk, chinups, 5, [20], chinups_weight, 6)
        createWorkoutItem(wrk, landmine, 5, [12], landmine_weight, 7)


        # Saturday
        g = createGroup(f"saturday-{w}")
        wrk = createWorkout(f"workout-{w}", g)

        createWorkoutItem(wrk, hill_sprints, 3, [10], [], 1)


print("BULLLLLL")
week531()