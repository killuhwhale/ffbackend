from datetime import datetime, timedelta
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.utils import InternalError, IntegrityError
from django.db.models import Q
from django.utils import timezone
from enum import Enum
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from typing import Any, Dict, List
import environ
import json
import pytz

from gyms.models import (
    GymClasses, Gyms, ResetPasswords, WorkoutGroups,
)
from utils import rev_preserve_day
from gyms.s3 import s3Client

User = get_user_model()
s3_client = s3Client()
tz = pytz.timezone("US/Pacific")
env = environ.Env()
environ.Env.read_env()

# When determining membership status give extra days.
MEMBERSHIP_LEEWAY = 0

# Limit for non members on how many workoutgroups they can create in a single day
NON_MEMBER_LIMIT = 1

GYM_FILES = 0
CLASS_FILES = 1
WORKOUT_FILES = 2
NAME_FILES = 3
USER_FILES = 4
COMP_WORKOUT_FILES = 5
FILES_KINDS = ['gyms', 'classes', 'workouts', "names", 'users', "completedWorkouts"]


def replace_tz_with_UTC(local_date, user_tz):
    """Replaces the local date with UTC TZ"""
    local_datetime = datetime.combine(local_date, datetime.min.time())
    user_timezone = pytz.timezone(user_tz)
    localized_dt = user_timezone.localize(local_datetime)
    return localized_dt.astimezone(pytz.utc)


def today_UTC(request):
    today = datetime.now(pytz.timezone(request.tz)).date()
    return replace_tz_with_UTC(today, request.tz)


def is_gymclass_member(user, gym_class):
    return user and gym_class and gym_class.classmembers_set.filter(
        user_id=user.id).exists()


def is_gymclass_coach(user, gym_class):
    return user and gym_class and gym_class.coaches_set.filter(
        user_id=user.id).exists()


def is_gym_class_owner(user, gym_class):
    return user and gym_class and str(user.id) == str(gym_class.gym.owner_id)


def is_member(request):
    """ Given a user return True if the user's sub_end_date is greater than two-days ago (leeway) """
    leeway = MEMBERSHIP_LEEWAY
    two_days_ago = today_UTC(request) - timedelta(days=leeway)
    return request.user.sub_end_date.replace(tzinfo=timezone.utc) > two_days_ago.replace(tzinfo=timezone.utc)


class ResponseError(Enum):
    GENERIC_ERROR = 0
    CREATE_LIMIT = 1


def to_err(msg: str, exception: Exception = None) -> Dict[str, Any]:
    '''
        Returns an error value.
    '''
    err_type = ResponseError.GENERIC_ERROR
    if is_limit_exception(exception):
        err_type = ResponseError.CREATE_LIMIT
    return {"error": msg, 'err_type': err_type.value}


def to_data(msg, data_type=0):
    return {"data": msg, 'data_type': data_type}


def is_gym_owner(user, gym_id):
    if not user or not gym_id:
        return False
    try:
        gym = Gyms.objects.get(id=gym_id)
        return str(gym.owner_id) == str(user.id)
    except Exception as e:
        print("Not gym owner: ", e, f'id: {gym_id}')
    return False


def upload_media(files, parent_id, file_kind, start_id=0):
    names = []
    last_idx = start_id
    for file in files:
        if not type(file) == type(""):
            ext = file.name.split(".")[-1]
            tmp_name = f"{last_idx}.{ext}"
            if s3_client.upload(file, file_kind, parent_id, tmp_name):
                last_idx += 1
                names.append(tmp_name)
    return names


def delete_media(parent_id, remove_media_ids, file_kind) -> Dict:
    ''' Removes media from WorkoutGroups, CompletedWorkoutGroups, WorkoutItems
        Structure is, for example:
          fitform/file_kind/parent_id/media_id.png
          fitform/gyms/1/main
          fitform/classes/1/logo
          fitform/users/1/profile_image
          fitform/workouts/1/1.png
          fitform/completedWorkouts/1/logo
          fitform/names/1/logo

    @parent_id: id of the WorkoutGroup/ CompleteWorkoutGroup etc...
    '''
    removed = {}
    for id in remove_media_ids:
        if s3_client.remove(file_kind, parent_id, id):
            removed[id] = ""
    return removed


def jbool(val: str) -> bool:
    return True if val == "true" else False


def is_limit_exception(e: Exception):
    ''' Returns True when the exception is an Error due to the limits set. '''
    if e is None:
        return False
    return type(e) == InternalError and str(e).startswith("Too many rows found")


def check_users_workouts_and_completed_today(request):
    # Check for a workoutGroup created today by user. If no workout, return True allow create
    user = request.user
    today = today_UTC(request)
    print("Checking w/ today:", today)
    try:
        workoutGroups = WorkoutGroups.objects.filter(
            owner_id=user.id,
            owned_by_class=False,
            archived=False,
            date__date=today
        )
        print("Found workoutgroups", workoutGroups)
        return len(workoutGroups) < NON_MEMBER_LIMIT
    except Exception as e:
        print("Error check_users_workouts_and_completed_today: ", e)
    return False


@transaction.atomic
def delete_user_data(user_id, user_email):
    try:
        combined_filter = Q(owner_id=user_id, owned_by_class=False)
        WorkoutGroups.objects.filter(combined_filter).delete()
        ResetPasswords.objects.filter(email=user_email).delete()
        User.objects.filter(id=user_id).delete()
        return True, ""
    except IntegrityError as ie:
        return False, str(ie)
    except Exception as e:
        print(f"An error occurred: {e}")
        return False, str(e)


def next_template_num(user, template_name):
    # Grab the next latest template number, default is 0, first one created will be 1
    latest_wg_by_template = WorkoutGroups.objects.filter(
        owner_id=user.id, template_name=template_name
    ).order_by("-template_num").first()
    return latest_wg_by_template.template_num + 1 if latest_wg_by_template else 1


def cur_template_num(user, template_name):
    # First one created will have 1 or larger
    latest_wg_by_template = WorkoutGroups.objects.filter(
        owner_id=user.id, template_name=template_name
    ).order_by("-template_num").first()
    return latest_wg_by_template.template_num if latest_wg_by_template else 0


class DestroyWithPayloadMixin(object):
    # Helps return a Response when deleting an entry, React native doesnt like nothing returned...
    def destroy(self, *args, **kwargs):
        serializer = self.get_serializer(self.get_object())
        super().destroy(*args, **kwargs)
        return Response(serializer.data, status=status.HTTP_200_OK)


class WorkoutGroupPagination(PageNumberPagination):
    # const PAGE_SIZE = 20;
    page_size = 20  # Must Match FrontEnd -> (apps) index.tsx
