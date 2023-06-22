from datetime import datetime
from gyms.models import Gyms, GymClasses, WorkoutGroups, Workouts, WorkoutItems, WorkoutNames, WorkoutCategories
from django.contrib.auth import get_user_model
import pytz
tz = pytz.timezone("US/Pacific")
'''

./manage.py shell < gyms/create_test_data.py


'''

User =  get_user_model()

user, nc = User.objects.get_or_create(
    email='t@t.com',
)
if nc:
    user.set_password("123")
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





squat, nc = WorkoutNames.objects.get_or_create(
    name= 'Squat',
)
bench, nc = WorkoutNames.objects.get_or_create(
    name= 'Bench press',
)
deadlift, nc = WorkoutNames.objects.get_or_create(
    name= 'Deadlift',
)
clean, nc = WorkoutNames.objects.get_or_create(
    name= 'Clean',
)
rollsesh, nc = WorkoutNames.objects.get_or_create(
    name= 'Roll session',
)


# TODO - Offset for_date so each workout show up on a different date.
# Regular Workout

workout_group, nc = WorkoutGroups.objects.get_or_create(
    owner_id= user.id,
    owned_by_class= False,
    finished= True,
    for_date= tz.localize(datetime.today()),
    title= "Regular Workout",
    caption= 'Testing',
)

workout, nc = Workouts.objects.get_or_create(
    group= workout_group,
    title= "My first regular workout",
    desc= "testing wod",
    scheme_type= 0,
    # "scheme_rounds": '[]',
)

item, nc = WorkoutItems.objects.get_or_create(**WorkoutItem(
    workout= workout,
    name= squat,
    sets= '3',
    reps= '[5]',
    weights= '[135,150,185] ',
    weight_unit= 'lb',
    order= 1,
).args())

item, nc = WorkoutItems.objects.get_or_create(**WorkoutItem(
    workout= workout,
    name= bench,
    sets= '5',
    reps= '[5]',
    weights= '[135,150,185, 205, 225]',
    weight_unit= 'lb',
    order= 2,
).args())

item, nc = WorkoutItems.objects.get_or_create(**WorkoutItem(
    workout= workout,
    name= deadlift,
    sets= '5',
    reps= '[5]',
    weights= '[135,150,185, 205, 225]',
    weight_unit= 'lb',
    order= 3,
).args())


# Reps Scheme Workout Diane

workout_group, nc = WorkoutGroups.objects.get_or_create(
    owner_id= user.id,
    owned_by_class= False,
    finished= True,
    for_date= tz.localize(datetime.today()),
    title= "Diane",
    caption= 'Testing',
)

workout, nc = Workouts.objects.get_or_create(
    group= workout_group,
    title= "My first regular workout",
    desc= "testing wod",
    scheme_type= 0,
    # "scheme_rounds": '[]',
)

item, nc = WorkoutItems.objects.get_or_create(**WorkoutItem(
    workout= workout,
    name= squat,
    sets= '3',
    reps= '[5]',
    weights= '[135,150,185] ',
    weight_unit= 'lb',
    order= 1,
).args())

item, nc = WorkoutItems.objects.get_or_create(**WorkoutItem(
    workout= workout,
    name= bench,
    sets= '5',
    reps= '[5]',
    weights= '[135,150,185, 205, 225] ',
    weight_unit= 'lb',
    order= 2,
).args())

item, nc = WorkoutItems.objects.get_or_create(**WorkoutItem(
    workout= workout,
    name= deadlift,
    sets= '5',
    reps= '[5]',
    weights= '[135,150,185, 205, 225] ',
    weight_unit= 'lb',
    order= 3,
).args())

