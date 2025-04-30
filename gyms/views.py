from datetime import datetime, time, timedelta
from django.utils import timezone
from enum import Enum
from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile
from django.contrib.auth import get_user_model
from django.contrib.postgres.search import TrigramSimilarity
from django.db import transaction
from django.db.utils import InternalError, IntegrityError
from django.db.models import Q, Max
from django.db.models.functions import Greatest
from django.http import JsonResponse
from itertools import chain
from PIL import Image
from instafitAPI import settings
from rest_framework import viewsets, status
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser, FileUploadParser
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import BasePermission, SAFE_METHODS
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory, force_authenticate
from typing import Any, Dict, List
import environ
import json
import pytz
import openai
import json
import tiktoken

from openai import OpenAI


from gyms.serializers import (
    CombinedWorkoutGroupsSerializerNoWorkouts, CompletedWorkoutCreateSerializer, CompletedWorkoutGroupsSerializer,
    CompletedWorkoutSerializer, GymClassSerializerWithWorkoutsCompleted, ProfileGymClassFavoritesSerializer, ProfileGymFavoritesSerializer,
    ProfileWorkoutGroupsSerializer, UserSerializer, UserWithoutEmailSerializer,
    WorkoutCategorySerializer, GymSerializerWithoutClasses,
    BodyMeasurementsSerializer, Gym_ClassSerializer, GymSerializer, GymClassCreateSerializer,
    GymClassSerializer, GymClassSerializerWithWorkouts, WorkoutGroupsCreateSerializer, WorkoutSerializer,
    WorkoutItemSerializer, WorkoutNamesSerializer, CoachesSerializer, ClassMembersSerializer,
    WorkoutDualItemSerializer, WorkoutDualItemCreateSerializer,
    WorkoutItemCreateSerializer, CoachesCreateSerializer, ClassMembersCreateSerializer,
    GymClassFavoritesSerializer, GymFavoritesSerializer, LikedWorkoutsSerializer, WorkoutGroupsSerializer,
    WorkoutCreateSerializer, ProfileSerializer, WorkoutNameMinimalSerializer, UserWorkoutMaxSerializer,
    UserWorkoutMaxHistorySerializer, WorkoutNameMaxSerializer,WorkoutGroupsAutoCompletedSerializer
)

from gyms.models import (TokenQuota,
    BodyMeasurements, CompletedWorkoutDualItems, CompletedWorkoutGroups, CompletedWorkoutItems,
    CompletedWorkouts, Gyms, GymClasses, ResetPasswords, UserWorkoutMax, UserWorkoutMaxHistory, WorkoutCategories, WorkoutStats, Workouts, WorkoutItems, WorkoutNames,
    Coaches, ClassMembers, GymClassFavorites, GymFavorites, LikedWorkouts, WorkoutGroups, WorkoutDualItems)
from utils import rev_preserve_day
from .s3 import s3Client

with open("gyms/create_workout_schema.json") as f:
    openai_schema = json.load(f)

tools = [
    {
        "type": "function",
        "function": {
           "name": openai_schema["name"],  # make sure your JSON includes this
            "description": openai_schema.get("description", "No description."),
            "parameters": openai_schema["parameters"]
        }
    }
]

client = OpenAI(api_key=settings.OPENAI_API_KEY)
tz = pytz.timezone("US/Pacific")
s3_client = s3Client()
env = environ.Env()
environ.Env.read_env()
User = get_user_model()

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
FILES_KINDS = ['gyms', 'classes', 'workouts',
               "names", 'users', "completedWorkouts"]



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
    leeway = MEMBERSHIP_LEEWAY  # Number of days of leeway

    # Calculate the date two days ago
    # two_days_ago = datetime.today() - timedelta(days=leeway)
    two_days_ago = today_UTC(request) - timedelta(days=leeway)

    # Check if the user's sub_end_date is greater than two days ago
    return request.user.sub_end_date.replace(tzinfo=timezone.utc) > two_days_ago.replace(tzinfo=timezone.utc)

class ResponseError(Enum):
    GENERIC_ERROR = 0
    CREATE_LIMIT = 1

def to_err(msg: str, exception: Exception=None)-> Dict[str, Any]:
    '''
        Returns an error value.
    '''
    err_type = ResponseError.GENERIC_ERROR
    if is_limit_exception(exception):
        err_type = ResponseError.CREATE_LIMIT

    return {
        "error": msg, 'err_type': err_type.value
    }


def to_data(msg, data_type=0):
    return {
        "data": msg, 'data_type': data_type
    }


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
    # print("Fiels", files)
    for file in files:
        if not type(file) == type(""):
            ext = file.name.split(".")[-1]
            tmp_name = f"{last_idx}.{ext}"
            if s3_client.upload(file, file_kind, parent_id, tmp_name):
                # If successful upload, inc index for file
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
    ''' Returns True when the exception is an Error due to the limits set.

        Limits set with Migration files as triggers.
        Gyms, GymClasses and Workouts are limited.

        Gyms = 3
        GymClasses = 3
        WorkoutGroups = 1
        Need to Add:
        CompletedWorkoutGroups.

        *Should also set limits to prevent users from completing everysingle workout or adding an absurd amount of workouts/ workoutItems to a single workout.
        - There might be FrontEnd restrictions on some of these but the backend should enforce it as well.

    '''
    if e is None: return False
    return type(e) == InternalError and str(e).startswith("Too many rows found")

class GymPermission(BasePermission):
    message = "Only Gym owners can remove their gym"

    def has_permission(self, request, view):
        if view.action == "update" or view.action == "partial_update" or request.method == "PATCH":
            return False
        elif request.method in SAFE_METHODS:
            # Check permissions for read-only request
            return True
        elif request.method == "POST" and view.action == "create":
            return is_member(request)
        elif request.method == "DELETE":
            gym_id = view.kwargs['pk']
            print("Deleting gym!!!!!!!!!!", gym_id, is_gym_owner(request.user, gym_id))

            gym = Gyms.objects.get(id=gym_id)
            print("Gym: ", gym)
            return is_gym_owner(request.user, gym_id)
        return False


class GymClassPermission(BasePermission):
    message = "Only Gym owners can create or remove classes"

    def has_permission(self, request, view):
        if view.action == "update" or view.action == "partial_update" or request.method == "PATCH":
            return False
        elif request.method in SAFE_METHODS:
            # Check permissions for read-only request
            return True
        elif request.method == "POST" and view.action == "create":
            return is_gym_owner(
                request.user,
                request.data.get("gym")
            ) and is_member(request)
        elif request.method == "DELETE":
            gym_class_id = view.kwargs['pk']
            return is_gym_class_owner(request.user, GymClasses.objects.get(id=gym_class_id))
        return False


class CoachPermission(BasePermission):
    message = """Only gym owners can create/delete a coach for their gymclasses."""

    def has_permission(self, request, view):
        # Need to check group id to see if the user has permission to do stuff.
        if view.action == "update" or view.action == "partial_update" or request.method == "PATCH":
            return False
        elif request.method in SAFE_METHODS:
            return True
        elif request.method == "POST" and view.action == "create":

            gym_class_id = request.data.get("gym_class", 0)
            if not gym_class_id:
                return Response(to_err("Error finding gym_class id"))

            user = request.user
            gym_class: GymClasses = GymClasses.objects.get(id=gym_class_id)
            owner_id = gym_class.gym.owner_id
            return str(owner_id) == str(user.id) and is_member(request)
        elif request.method == "DELETE":
            if not request.resolver_match.url_name == 'coaches-remove':
                return False
            member_id = request.data.get("user_id")
            member = ClassMembers.objects.get(id=member_id)
            gym_class_id = member.gym_class.id
            gym_class: GymClasses = GymClasses.objects.get(id=gym_class_id)
            owner_id = gym_class.gym.id
            return str(owner_id) == str(request.user.id)

class MemberPermission(BasePermission):
    message = """Only gym owners or coaches can create/delete a member for their gymclasses."""

    def has_permission(self, request, view):
        # Need to check group id to see if the user has permission to do stuff.


        if view.action == "update" or view.action == "partial_update" or request.method == "PATCH":
            return False
        elif request.method in SAFE_METHODS:
            return True
        elif request.method == "POST" and view.action == "create":
            gym_class_id = request.data.get("gym_class", 0)
            if not gym_class_id:
                return Response(to_err("Error finding gym_class id"))

            gym_class: GymClasses = GymClasses.objects.get(id=gym_class_id)
            return (is_gym_owner(request.user, gym_class.gym.id) or is_gymclass_coach(request.user, gym_class)) and is_member(request)
        elif request.method == "DELETE":
            if not request.resolver_match.url_name == 'classmembers-remove':
                return False

            member_id = request.data.get("user_id")
            member = ClassMembers.objects.get(id=member_id)
            gym_class_id = member.gym_class.id
            gym_class: GymClasses = GymClasses.objects.get(id=gym_class_id)
            return is_gym_owner(request.user, gym_class.gym.id) or is_gymclass_coach(request.user, gym_class)



class WorkoutPermission(BasePermission):
    message = """Only users can create/delete workouts for themselves or for a class they own or are a coach of."""

    def has_permission(self, request, view):
        # Need to check group id to see if the user has permission to do stuff.
        print(f"{request.method=} - {view.action=}")
        if view.action == "partial_update" or request.method == "PATCH":
            return False
        elif request.method in SAFE_METHODS:
            return True
        elif request.method == "POST" and view.action == "create" or request.method == "PUT":
            group_id = request.data.get("group", 0)
            if not group_id:
                return Response(to_err("Error finding group id"))

            workout_group: WorkoutGroups = WorkoutGroups.objects.get(
                id=group_id)
            owner_id = workout_group.owner_id

            if workout_group.owned_by_class:
                gym_class = GymClasses.objects.get(id=owner_id)
                # print("PPERM check:", is_gym_owner(request.user, gym_class.gym.id), is_gymclass_coach(request.user, gym_class))
                return is_gym_owner(request.user, gym_class.gym.id) or is_gymclass_coach(request.user, gym_class)
            return not workout_group.owned_by_class and str(owner_id) == str(request.user.id)
        elif request.method == "DELETE":
            workout_id = view.kwargs['pk']
            workout = Workouts.objects.get(id=workout_id)
            workout_group_id = workout.group.id
            workout_group = WorkoutGroups.objects.get(id=workout_group_id)
            owned_by_class = workout_group.owned_by_class

            print("Delete workout ", workout_id, owned_by_class,
                  request.user.id, workout_group.owner_id)
            if owned_by_class:
                gym_class = GymClasses.objects.get(id=workout_group.owner_id)
                print("Delet class owned workout:", request.user.id, gym_class.gym.id, is_gym_owner(
                    request.user, gym_class.gym.id), is_gymclass_coach(request.user, gym_class))
                return is_gym_owner(request.user, gym_class.gym.id) or is_gymclass_coach(request.user, gym_class)
            else:
                return not owned_by_class and str(request.user.id) == str(workout_group.owner_id)



class SuperUserWritePermission(BasePermission):
    message = """Only admins can create/delete workoutNames."""

    def has_permission(self, request, view):
        if view.action == "update" or view.action == "partial_update" or request.method == "PATCH":
            return False
        elif request.method in SAFE_METHODS:
            # Check permissions for read-only request
            return True
        elif request.method == "POST" and view.action == "create":
            return request.user.is_superuser

        elif request.method == "DELETE":
            return request.user.is_superuser
        return False


def check_users_workouts_and_completed_today(request):
    # Check for a workoutGroup created today by user. If no workout, return True allow create
    user = request.user
    tz = request.tz
    # today = datetime.now( pytz.timezone(tz)).date()
    # today = timezone.now().date()
    today = today_UTC(request)

    workoutGroups = WorkoutGroups.objects.filter(
        owner_id=user.id,
        owned_by_class=False,
        archived=False,
        date__date=today
    )
    return len(workoutGroups) < NON_MEMBER_LIMIT
    # if len(workoutGroups) > 0:
    #     return False

    # completedWorkoutGroups = CompletedWorkoutGroups.objects.filter(
    #     user_id=user.id,
    #     date__date=today
    # )
    # return len(completedWorkoutGroups) == 0 # Allow if nothing is created today

class WorkoutGroupsPermission(BasePermission):
    message = """Only users can create/delete workouts for themselves or
                for a class they own or are a coach of."""

    def has_permission(self, request, view):

        print("WorkoutGroup Perm: ",  request.method, view.action)

        if view.action == "update" or view.action == "partial_update" or request.method == "PATCH":
            return False
        elif request.method in SAFE_METHODS:
            # Check permissions for read-only request
            return True
        elif request.method == "POST" and (view.action == "create" or view.action == "duplicate"):
            '''
                A user can create workouts if they are members.
                If a user is not a member:
                    - Workouts for classes cannot be created.
                    - Workouts for users can only be created once per day including Completed Workouts
            '''

            user_is_member = is_member(request)

            if jbool(request.data.get("owned_by_class")):
                # Verify user is owner or coach of class and is a member
                gym_class = GymClasses.objects.get(
                    id=request.data.get("owner_id"))
                print("Checking wg perm for class: ", is_gym_owner(
                    request.user, gym_class.gym.id) or is_gymclass_coach(request.user, gym_class))
                return (is_gym_owner(request.user, gym_class.gym.id) or is_gymclass_coach(request.user, gym_class)) and user_is_member

            # user can only add 1 workout per day if they are not a member.
            if user_is_member:
                return not jbool(request.data.get("owned_by_class")) and \
                    str(request.user.id) == str(request.data.get("owner_id"))
            else:
                return check_users_workouts_and_completed_today(request)


        elif request.method == "DELETE":
            # If owned_by_class
            workout_group_id = view.kwargs['pk']
            workout_group = WorkoutGroups.objects.get(id=workout_group_id)
            owned_by_class = workout_group.owned_by_class
            if owned_by_class:
                gym_class = GymClasses.objects.get(id=workout_group.owner_id)
                return is_gym_owner(request.user, gym_class.gym.id) or is_gymclass_coach(request.user, gym_class)
            else:
                return not owned_by_class and str(request.user.id) == str(workout_group.owner_id)

        return False


class EditWorkoutMediaPermission(BasePermission):
    message = """Only users can edit workouts for themselves or
                for a class they own or are a coach of."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            # Check permissions for read-only request
            return True
        elif request.method == "POST" or request.method == "DELETE":
            workout_id = view.kwargs['pk']
            workout = Workouts.objects.get(id=workout_id)
            if workout.owned_by_class:
                gym_class = GymClasses.objects.get(id=workout.owner_id)
                return is_gym_class_owner(request.user, gym_class) or is_gymclass_coach(request.user, gym_class)
            else:
                return str(request.user.id) == str(workout.owner_id)

        return False


class WorkoutItemsPermission(BasePermission):
    message = """Only users can create workout Items for themselves or for a class they own or are a coach of."""

    def has_permission(self, request, view):
        # Workout Items are create in bulk and are not modified nor deleted directly.
        # print("WorkoutITems 403 checkkkkzzzz", request.method, type(view.action))
        if view.action == "create"  or view.action == "partial_update" or view.action == "destroy":
            return False
        elif request.method in SAFE_METHODS:
            # Check permissions for read-only request
            return True



        elif request.method == "POST" and (view.action == "items" or  view.action == "update_items"):
            workout_id = request.data.get("workout", "0")
            print("Perm check workoutItems", workout_id)
            if not workout_id == "0":
                workout, workout_group = None, None
                try:
                    workout = Workouts.objects.get(id=workout_id)
                    workout_group = WorkoutGroups.objects.get(id=workout.group.id)
                except Exception as e:
                    print("Error: ", e)
                    return False
                if not workout or not workout_group:
                    return False

                owner_id = workout_group.owner_id
                owned_by_class = workout_group.owned_by_class
                # TODO() microservice hit other service to validate ownership
                if owned_by_class:
                    # Verify user is owner or coach of class.
                    gym_class = GymClasses.objects.get(
                        id=owner_id)
                    return is_gymclass_coach(request.user, gym_class) or is_gym_class_owner(request.user, gym_class)
                else:
                    return str(request.user.id) == str(owner_id)
        return False

class WorkoutDualItemsPermission(BasePermission):
    message = """Only users can create workout Items for themselves or for a class they own or are a coach of."""

    def has_permission(self, request, view):
        # Workout Items are create in bulk and are not modified nor deleted directly.
        # print("WorkoutITemsDual 403 checkkkk", request.method, view.action)
        if view.action == "create" or view.action == "update" or view.action == "partial_update" or view.action == "destroy":
            return False
        elif request.method in SAFE_METHODS:
            # Check permissions for read-only request
            return True
        # elif request.method == "POST" and view.action == "record_items":
        #     return True

        elif request.method == "POST" and (view.action == "items" or view.action == "update_items" or view.action == "record_items"):
            workout_id = request.data.get("workout", "0")
            print("Perm check workoutItems", workout_id)
            if not workout_id == "0":
                workout, workout_group = None, None
                try:
                    workout = Workouts.objects.get(id=workout_id)
                    workout_group = WorkoutGroups.objects.get(id=workout.group.id)
                except Exception as e:
                    print("Error: ", e)
                    return False
                if not workout or not workout_group:
                    return False

                owner_id = workout_group.owner_id
                owned_by_class = workout_group.owned_by_class
                # TODO() microservice hit other service to validate ownership
                if owned_by_class:
                    # Verify user is owner or coach of class.
                    gym_class = GymClasses.objects.get(
                        id=owner_id)
                    return is_gymclass_coach(request.user, gym_class) or is_gym_class_owner(request.user, gym_class)
                else:
                    return str(request.user.id) == str(owner_id)
        return False


class CompletedWorkoutGroupsPermission(BasePermission):
    message = """Only users can create/delete completed workoutgroups for themselves."""

    def has_permission(self, request, view):
        if view.action == "update" or view.action == "partial_update" or request.method == "PATCH":
            return False
        elif request.method in SAFE_METHODS:
            # Check permissions for read-only request
            return True
        elif request.method == "POST" and view.action == "create":
            # API will create the CompletedWorkoutGroup for the requesting user.
            if is_member(request):
                print("Completed perms: is member")
                return True
            else:
                print("Completed perms: checking nnon members")
                return check_users_workouts_and_completed_today(request)

        elif request.method == "DELETE":
            comp_workout_group_id = view.kwargs['pk']
            comp_workout_group = CompletedWorkoutGroups.objects.get(id=comp_workout_group_id)
            return str(comp_workout_group.user_id) == str(request.user.id)

        return False

class CompletedWorkoutsPermission(BasePermission):
    message = """Only users can create/delete completed workouts for themselves."""

    def has_permission(self, request, view):
        if view.action == "create" or view.action == "update" or view.action == "partial_update" or request.method == "PATCH":
            return False
        elif request.method in SAFE_METHODS:
            # Check permissions for read-only request
            return True
        elif request.method == "POST" and view.action == "create":
            # Completed Workouts are created at CompletedWorkoutGroup creation
            return False
        elif request.method == "DELETE":

            comp_workout_id = view.kwargs['pk']
            comp_workout = CompletedWorkouts.objects.get(id=comp_workout_id)
            return str(comp_workout.user_id) == str(request.user.id)

        return False


class UserMaxesPermission(BasePermission):
    message = """UserMaxesPermission: Only users can perform actions for themselves."""

    def has_permission(self, request, view):

        target_user_id = None
        if request.method in SAFE_METHODS:
            target_user_id = request.query_params.get("user_id")
        else:
            target_user_id = str(request.data.get("user_id"))

        print("User self action perm: ", target_user_id, request.user.id)
        return target_user_id == str(request.user.id)

class SelfActionPermission(BasePermission):
    message = """
        Only users can perform actions for themselves.
            GET => ?user_id=id
            POST => { user_id: id }
    """

    def has_permission(self, request, view):


        target_user_id = None
        print("Usererzzzzz: ", request.data.keys())
        if request.method in SAFE_METHODS:
            target_user_id = request.query_params.get("user_id")
        else:
            target_user_id = str(request.data.get("user_id"))

        print("User self action perm: ", target_user_id, request.user.id)
        return target_user_id == str(request.user.id)


class DestroyWithPayloadMixin(object):
    # Helps return a Response when deleting an entry, React native doesnt like nothing returned...
    def destroy(self, *args, **kwargs):
        serializer = self.get_serializer(self.get_object())
        super().destroy(*args, **kwargs)
        return Response(serializer.data, status=status.HTTP_200_OK)


########################################################
#   ////////////////////////////////////////////////   #
########################################################



""" - Gym Removal
    1. Get all classes
    2. For ea class, mark wodGroups as archived.
    3. Remove all Coaches, members  and favorites
    4. Delete each class
    5. Delete gym

    - GymClass Removal
    1. Mark wodGroups as archived.
    2. Remove all Coaches, members  and favorites
    3. Delete each class
    4. Delete gym

    def remove_gym():
        for gclass in gymClasses:
            remove_gym_class(gclass)
        gym.delete()

    def remove_gym_class(gymClass):
        # Steps 1-4
"""

# def remove_gym_class(gym_class: GymClasses):
#     try:
#         workout_groups = WorkoutGroups.objects.filter(owned_by_class=True, owner_id=gym_class.id)
#         for wg in workout_groups:
#             wg.archived = True
#         WorkoutGroups.objects.bulk_update(workout_groups, ["archived"])

#         GymClassFavorites.objects.filter(gym_class=gym_class).delete()
#         Coaches.objects.filter(gym_class=gym_class).delete()
#         ClassMembers.objects.filter(gym_class=gym_class).delete()
#         gym_class.delete()
#         return True
#     except Exception as err:
#         print(f"Error removing gym class: ", err)
#     return False

# @transaction.atomic
# def remove_gym(gym: Gyms):
#     with transaction.atomic():
#         gym_classes = gym.gymclasses_set.all()
#         for gc in gym_classes:
#             remove_gym_class(gc)

#         GymFavorites.objects.filter(gym=gym).delete()
#         transaction.commit()
#         return True
#     # except Exception as err:
#     #     print(f"Error removing gym: ", err)
#     return False





class GymViewSet(DestroyWithPayloadMixin, viewsets.ModelViewSet, GymPermission):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = Gyms.objects.all()
    serializer_class = GymSerializer
    permission_classes = [GymPermission]

    # parser_classes = [MultiPartParser, FileUploadParser]

    def create(self, request):
        try:
            data = request.data.copy().dict()
            print(request.FILES, data)
            main = request.data.get("main")
            logo = request.data.get("logo")

            data['owner_id'] = request.user.id
            if 'main' in data:
                del data['main']

            if 'logo' in data:
                del data['logo']

            gym = Gyms.objects.create(**data)
            # if not newly_created:
            #     print("Gym already created. Must delete and reupload w/ media or edit gym.")
            #     return Response(to_err("Gym already created. Must delete and reupload w/ media or edit gym."))

            parent_id = gym.id
            if main:
                print("Uploading main image")
                main_uploaded = s3_client.upload(
                    main, FILES_KINDS[GYM_FILES], parent_id, "main")
                if not main_uploaded:
                    return Response(to_err("Failed to upload main image"))
            if logo:
                print("Uploading main image")
                logo_uploaded = s3_client.upload(
                    logo, FILES_KINDS[GYM_FILES], parent_id, "logo")
                if not logo_uploaded:
                    return Response(to_err("Failed to upload logo"))

            print("Gym created successfully", gym)
            return Response(GymSerializer(gym).data)
        except Exception as e:
            print("Failed to create Gym ", e)
            return Response(to_err(f"Failed to create Gym: {e}", exception=e), status=422)

    @action(detail=True, methods=['get'], permission_classes=[])
    def user_favorites(self, request, pk=None):
        try:
            user_id = pk
            return Response(GymFavoritesSerializer(GymFavorites.objects.filter(user_id=user_id), many=True).data)
        except Exception as e:
            print(e)
            return Response(to_err("Failed get user's favorite gyms."))

    @action(detail=False, methods=['post'], permission_classes=[])
    def favorite(self, request, pk=None):
        try:
            user_id = request.user.id
            gym_id = request.data.get("gym")

            GymFavorites.objects.create(
                user_id=user_id, gym=Gyms.objects.get(id=gym_id))
            return Response(to_data("Favorited!"))
        except Exception as e:
            print(e)
            return Response(to_err("Failed to favorite"))

    @action(detail=False, methods=['DELETE'], permission_classes=[])
    def unfavorite(self, request, pk=None):
        try:
            user_id = request.user.id
            gym_id = request.data.get("gym")
            GymFavorites.objects.get(user_id=user_id, gym=gym_id).delete()
            return Response(to_data("Unfavorited!"))
        except Exception as e:
            return Response(to_err("Failed to unfavorite"))

    @action(detail=True, methods=['get'], permission_classes=[])
    def gymsclasses(self, request, pk=None):
        # Choose serilizer per entry if the user should view it or not....
        try:
            gym = self.queryset.get(id=pk)
            '''
                This returns a gym with all classes.... The classes should be able to be viewed but not the workouts or class members....
            '''
            return Response(GymSerializer(gym).data)
        except Exception as e:
            print(e)
        return Response({})

    @action(detail=True, methods=['PATCH'], permission_classes=[])
    def edit_media(self, request, pk=None):
        # try:
        gym_id = pk
        main_file = request.data.get("main", None)
        logo_file = request.data.get("logo", None)

        gym = Gyms.objects.get(id=gym_id)

        parent_id = gym.id
        if main_file:
            s3_client.upload(
                main_file, FILES_KINDS[GYM_FILES], parent_id, "main")
        if logo_file:
            s3_client.upload(
                logo_file, FILES_KINDS[GYM_FILES], parent_id, "logo")

        return Response(to_data("Successfully added media to gym."))

        # except Exception as e:
        #     print(e)
        #     return Response("Failed to add media to workout")

    @action(detail=False, methods=['GET'], permission_classes=[])
    def user_gyms(self, request, pk=None):
        user_id = request.user.id
        if not user_id:
            return Response({'error': 'user not found'})

        gyms = Gyms.objects.filter(owner_id=user_id)
        return Response(GymSerializerWithoutClasses(gyms, many=True).data)

    def get_serializer_class(self):
        if self.action == 'list':
            return GymSerializerWithoutClasses
        return GymSerializer

    def get_queryset(self):
        '''Affects destroy!'''
        if self.request.method == "DELETE":
            return super().get_queryset()

        # Apply any filtering or ordering here
        queryset = super().get_queryset().order_by('title')  # Need to order by rating... and need to add rating
        queryset = queryset[:40]
        return queryset

class GymClassViewSet(DestroyWithPayloadMixin, viewsets.ModelViewSet, GymClassPermission):
    permission_classes = [GymClassPermission]
    queryset = GymClasses.objects.all().select_related('gym')

    def create(self, request):
        try:
            data = request.data.copy().dict()
            main = request.data.get("main")
            logo = request.data.get("logo")
            if 'main' in data:
                del data['main']
            if 'logo' in data:
                del data['logo']

            data['private'] = jbool(data['private'])
            gym = Gyms.objects.get(id=data.get('gym'))
            gym_class, newly_created = GymClasses.objects.get_or_create(
                **{**data, "gym": gym})
            if not newly_created:
                return Response(to_err("Gym class already created. Must delete and reupload w/ media or edit gym class."))

            parent_id = gym_class.id
            if main:
                print("Uploading main class image")
                main_uploaded = s3_client.upload(main, FILES_KINDS[CLASS_FILES], parent_id, "main")
                if not main_uploaded:
                    return Response(to_err("Failed to upload main class image"))

            if logo:
                print("Uploading logo class image")
                logo_uploaded = s3_client.upload(logo, FILES_KINDS[CLASS_FILES], parent_id, "logo")
                if not logo_uploaded:
                    return Response(to_err("Failed to upload logo class image"))

            return Response(GymClassCreateSerializer(gym_class).data)
        except Exception as e:
            print(e)
            return Response(to_err(f"Failed to create gymclass: {e}", exception=e), status=422)

    @action(detail=True, methods=['get'], permission_classes=[])
    def user_favorites(self, request, pk=None):
        try:
            user_id = pk
            return Response(GymClassFavoritesSerializer(GymClassFavorites.objects.filter(user_id=user_id), many=True).data)
        except Exception as e:
            print(e)
            return Response(to_err("Failed get user's favorite gym classes."))

    @action(detail=False, methods=['post'], permission_classes=[])
    def favorite(self, request, pk=None):
        try:
            user_id = request.user.id
            gym_class_id = request.data.get("gym_class")
            GymClassFavorites.objects.create(
                user_id=user_id, gym_class=GymClasses.objects.get(id=gym_class_id))
            return Response(to_data("Favorited!"))
        except Exception as e:
            print(e)
            return Response(to_err("Failed to favorite"))

    @action(detail=False, methods=['DELETE'], permission_classes=[])
    def unfavorite(self, request, pk=None):
        try:
            user_id = request.user.id
            gym_class_id = request.data.get("gym_class")
            GymClassFavorites.objects.get(
                user_id=user_id, gym_class=GymClasses.objects.get(id=gym_class_id)).delete()
            return Response(to_data("Unfavorited!"))
        except Exception as e:
            return Response(to_err("Failed to unfavorite"))

    @action(detail=True, methods=['get'], permission_classes=[])
    def workouts(self, request, pk=None):
        '''
            GymClass view, gets all related data for a GymClass.

            only returned finished workouts unless the requesting user owns them
        '''
        user_id = request.user.id
        gym_class = None
        try:
            gym_class: GymClasses = self.queryset.get(id=pk)
        except Exception as e:
            print(e)
            return Response(to_err("Invalid class"))

        # If user is member or coach, they can see workouts from class...
        workout_groups = []  # Empty queryset

        # Requesting user

        # 1. is regular, non owner should only see WorkoutGroups finished
        # - private matters here
        # 2. User is owner or coach of class, can see unfinished
        # - private does not matter here because we already know the user is owner/coach
        user_is_member = is_gymclass_member(request.user, gym_class)
        user_is_coach = is_gymclass_coach(request.user, gym_class)
        user_is_owner = is_gym_owner(request.user, gym_class.gym.id)
        is_private = gym_class.private

        # Microservice TODO('Make request to workouts service')
        workout_groups = None
        if user_is_owner or user_is_coach:
            # Show eveything
            workout_groups = WorkoutGroups.objects.filter(
                owner_id=pk,
                owned_by_class=True,
                archived=False
            ).order_by('-for_date')
        elif is_private and user_is_member or not is_private:
            # Show finished workouts
            workout_groups = WorkoutGroups.objects.filter(
                owner_id=pk,
                owned_by_class=True,
                finished=True,
                archived=False,
            ).order_by('-for_date')

        # Return from Microservice
        gym_class.workoutgroups_set = workout_groups

        user_can_edit = user_is_owner or user_is_coach

        print(f"User can edit {user_can_edit}")

        return Response({
            **GymClassSerializerWithWorkoutsCompleted(gym_class, context={'request': request, }).data,
            "user_can_edit": user_can_edit,
            "user_is_owner": user_is_owner,
            "user_is_coach": user_is_coach,
            "user_is_member": user_is_member,
        })

    def get_serializer_class(self):
        if self.action == 'list' or self.action == 'retrieve':
            return GymClassSerializer
        if self.action == 'create':
            return GymClassCreateSerializer
        return GymClassSerializer

    @action(detail=True, methods=['PATCH'], permission_classes=[])
    def edit_media(self, request, pk=None):
        gym_class_id = pk
        main_file = request.data.get("main", None)
        logo_file = request.data.get("logo", None)

        gym_class = GymClasses.objects.get(id=gym_class_id)

        parent_id = gym_class.id
        if main_file:
            s3_client.upload(
                main_file, FILES_KINDS[CLASS_FILES], parent_id, "main")
        if logo_file:
            s3_client.upload(
                logo_file, FILES_KINDS[CLASS_FILES], parent_id, "logo")

        return Response(to_data("Successfully added media to gym class."))

    def get_queryset(self):
        '''Affects destroy!'''
        if self.request.method == "DELETE":
            return super().get_queryset()

        # Apply any filtering or ordering here
        queryset = super().get_queryset().order_by('date')  # Need to order by rating... and need to add rating
        queryset = queryset[:40]
        return queryset

########################################################
#   ////////////////////////////////////////////////   #
########################################################



def has_unfinished_workoutgroups(workout_group):
    # This is a workoutGroup that is a part of the template
    template_name = workout_group.template_name
    template_num = workout_group.template_num
    has_unfinished_workoutgroups_in_template = WorkoutGroups.objects.filter(
            owner_id=workout_group.owner_id,
            template_name=template_name,
            template_num=template_num,
            finished=False
        ).exclude(id=workout_group.id).exists()

    return has_unfinished_workoutgroups_in_template


class WorkoutGroupsViewSet(viewsets.ModelViewSet, WorkoutGroupsPermission):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = WorkoutGroups.objects.all()
    serializer_class = WorkoutGroupsSerializer
    permission_classes = [WorkoutGroupsPermission]

    def create_group(self, data, request):
        try:

            # Models expects True/ False, coming from json, we get true/ false. Instead we store 0,1 and convert
            if not data['owned_by_class']:
                data['owner_id'] = request.user.id

            workout_group, newly_created = WorkoutGroups.objects.get_or_create(
                **{**data, 'media_ids': []})
            if not newly_created:
                return Response(to_err("Workout already created. Must delete and reupload w/ media or edit workout.", ))
        except Exception as e:
            print("Error creating workout group:", e)
            return Response(to_err(f"Error creating workout group: {e}", exception=e), status=422)
        return Response(WorkoutGroupsSerializer(workout_group, context={'request': request}).data)
        # try:
        #     parent_id = workout_group.id
        #     print("Uploading workout files...", files)
        #     uploaded_names = upload_media(
        #         files, parent_id, FILES_KINDS[WORKOUT_FILES])

        #     if not len(files) == len(uploaded_names):
        #         workout_group.delete()
        #         return Response(to_err("Media not uploaded."))

        #     workout_group.media_ids = json.dumps([n for n in uploaded_names])
        #     workout_group.save()
        #     return Response(WorkoutGroupsSerializer(workout_group, context={'request': request}).data)
        # except Exception as e:
        #     workout_group.delete()
        #     print("Error Uploading media for workoutgroup ", e)
        #     return Response(to_err("Failed to create workout"))

    def create(self, request):
        data = {**request.data.dict()}
        data['owned_by_class'] = jbool(data['owned_by_class'])
        if 'files' in data:
            del data['files']
        files = request.data.getlist("files", [])

        return self.create_group(data, request)

    @action(detail=False, methods=['post'], permission_classes=[WorkoutGroupsPermission])
    def duplicate(self, request, *args, **kwargs):
        data = {**request.data.dict()}
        data['owned_by_class'] = jbool(data['owned_by_class'])
        title = data['title']
        for_date = data['for_date']
        caption = data['caption']
        owned_by_class = data['owned_by_class']
        owner_id = data['owner_id']
        workouts = json.loads(data['workouts'])

        group_data = {
            "title": title,
            "for_date": for_date,
            "caption": caption,
            "owned_by_class": owned_by_class,
            "owner_id": owner_id,
            "finished": False,
            "media_ids": [],
            "archived": False,
        }

        if not group_data['owned_by_class']:
            group_data['owner_id'] = request.user.id

        with transaction.atomic():
            workout_group, newly_created = WorkoutGroups.objects.get_or_create(**{**group_data, 'media_ids': []})

            for workout_json in workouts:
                items = workout_json['workout_items']
                del workout_json['workout_items']
                del workout_json['id']


                print(f"{workout_json=}")
                workout_stats_json =  workout_json['stats']
                del workout_json['stats']


                workout_data = {**workout_json, 'group_id': workout_group.id}
                del workout_data['group']
                print(f"{workout_data=}")

                workout, new_or_nah = Workouts.objects.get_or_create(**workout_data)
                print(f'Got Workout ({new_or_nah=}):', f"{workout.scheme_type=}")
                workout_stats = WorkoutStats.objects.create(workout=workout, tags=workout_stats_json['tags'], items=workout_stats_json['items'])
                print(f'Created WorkoutState {workout_stats=}')

                new_items = []
                for item_json in items:
                    del item_json['id']
                    del item_json['date']

                    if  workout.scheme_type <= 2:
                        new_items.append(WorkoutItems(
                            **{**item_json, "workout": Workouts(id=workout.id), "name": WorkoutNames(id=item_json['name']['id'])}))
                    else:
                        # Create Dual Items
                         new_items.append(WorkoutDualItems(
                            **{**item_json, "workout": Workouts(id=workout.id), "name": WorkoutNames(id=item_json['name']['id'])}))

                if  workout.scheme_type <= 2:
                    WorkoutItems.objects.bulk_create(new_items)
                else:
                    WorkoutDualItems.objects.bulk_create(new_items)



        return Response(WorkoutGroupsSerializer(workout_group, context={'request': request}).data)
        # workouts = json.loads(data['workouts'])
        # for workout in workouts:

        # Create Workouts with items


    def last_id_from_media(self, cur_media_ids: List[str]) -> int:
        last_id = 0
        if not cur_media_ids:
            return last_id

        # Items shoudl remain in order but we will ensure by sorting.
        # This should have little impact when limiting each workout to 5-7 posts.
        media_ids = sorted(cur_media_ids, key=lambda p: p.split(".")[0])
        last_media_id = media_ids[-1]
        return int(last_media_id.split(".")[0])

    @action(detail=True, methods=['post'], permission_classes=[EditWorkoutMediaPermission])
    def add_media_to_workout(self, request, pk=None):
        # try:
        workout_group_id = pk
        files = request.data.getlist("files")

        workout_group = WorkoutGroups.objects.get(id=workout_group_id)
        cur_media_ids = sorted(json.loads(workout_group.media_ids))

        last_id = self.last_id_from_media(cur_media_ids)

        print("Last id: ", last_id)
        uploaded_names = upload_media(
            files, workout_group.id, FILES_KINDS[WORKOUT_FILES], start=last_id + 1)
        print("Num uploaded: ", uploaded_names)

        print("Cur media ids: ", cur_media_ids)
        cur_media_ids.extend(uploaded_names)

        print("Updated Cur media ids: ", cur_media_ids)
        workout_group.media_ids = json.dumps(cur_media_ids)
        workout_group.save()
        return Response(to_data("Successfully added media to workout"))

        # except Exception as e:
        #     print(e)
        #     return Response("Failed to add media to workout")

    @action(detail=True, methods=['delete'], permission_classes=[EditWorkoutMediaPermission])
    def remove_media_from_workout(self, request, pk=None):
        try:
            workout_group_id = pk
            remove_media_ids = json.loads(request.data.get("media_ids"))
            workout_group = WorkoutGroups.objects.get(id=workout_group_id)
            cur_media_ids = sorted(json.loads(workout_group.media_ids))
            deleted_ids = delete_media(
                workout_group.id, remove_media_ids, FILES_KINDS[WORKOUT_FILES])

            cur_media_ids = list(
                filter(lambda n: not str(n) in deleted_ids, cur_media_ids))
            print("Filtered Current media ids: ", cur_media_ids)
            workout_group.media_ids = json.dumps(cur_media_ids)
            workout_group.save()
            return Response(to_data("Deleted"))
        except Exception as e:
            print(e)
            return Response(to_err("Failed to remove media"))

    @ action(detail=True, methods=['get'], permission_classes=[])
    def user_workouts(self, request, pk=None):
        try:

            owner_id = request.user.id
            print("Owner id", owner_id)
            workout_groups: WorkoutGroups = WorkoutGroups.objects.get(
                owner_id=owner_id, owned_by_class=False, id=pk)
            # // Workout group is single group with multiple workouts
            return Response(WorkoutGroupsSerializer(workout_groups, context={'request': request, }).data)
        except Exception as e:
            print("\n\n\n\n\nWorkoutGroupsViewSet user_workouts", e)
            print("Request", request)
            return Response({'error': "Failed get user's workout group."}, status=500)
    @ action(detail=False, methods=['get'], permission_classes=[SelfActionPermission])
    def last_x_workout_groups(self, request, pk=None):
        # try:
        owner_id = request.user.id
        # workout_groups: WorkoutGroups = WorkoutGroups.objects.filter(
        #     owner_id=owner_id, owned_by_class=False, for_date__lt=today_UTC(request))


        workout_groups = (
            WorkoutGroups.objects
            .filter(owner_id=owner_id, owned_by_class=False, for_date__lt=today_UTC(request))
            .order_by('-for_date')[:10]
        )
        # .order_by('-for_date')[:10]

        return Response(WorkoutGroupsSerializer(workout_groups, many=True, context={'request': request, }).data)
        # except Exception as e:
        #     print("\n\n\n\n\nWorkoutGroupsViewSet user_workouts", e)
        #     print("Request", request)
        #     return Response({'error': "Failed get user's workout group."}, status=500)



    @ action(detail=True, methods=['get'], permission_classes=[])
    def class_workouts(self, request, pk=None):
        ''' Returns all workouts for a gymclass.
        '''
        try:
            workout_group_id = pk
            return Response(
                WorkoutGroupsSerializer(
                    WorkoutGroups.objects.get(id=workout_group_id),
                    context={'request': request, }
                ).data
            )
        except Exception as e:
            print(e)
            return Response(to_err("Failed get Gym class's workouts."))

    @ action(detail=False, methods=['post'], permission_classes=[SelfActionPermission])
    def favorite(self, request, pk=None):
        try:
            user_id = request.data.get("user_id")
            workout_id = request.data.get("workout")
            LikedWorkouts.objects.create(
                user_id=user_id, workout=workout_id)
            return Response(to_data("Favorited!"))
        except Exception as e:
            return Response(to_err("Failed to favorite"))

    @ action(detail=False, methods=['DELETE'], permission_classes=[SelfActionPermission])
    def unfavorite(self, request, pk=None):
        try:
            user_id = request.data.get("user_id")
            workout_id = request.data.get("workout")
            LikedWorkouts.objects.get(
                user_id=user_id, workout=workout_id).delete()
            return Response(to_data("Unfavorited!"))
        except Exception as e:
            return Response(to_err("Failed to unfavorite"))


    @ action(detail=False, methods=['POST'], permission_classes=[SelfActionPermission])
    def update_title(self, request, pk=None):
        wid = request.data['id']
        updated_title = request.data['title']

        if updated_title:
            grp = WorkoutGroups.objects.get(id=wid)
            if grp:
                print("Updating title to: ", updated_title)
                grp.title = updated_title
                grp.save()
                return Response({"data": 'successfully updated title'})
        return Response({"err": 'Failed to update title'})

    @ action(detail=False, methods=['POST'], permission_classes=[SelfActionPermission])
    def update_caption(self, request, pk=None):
        wid = request.data['id']
        updated_caption = request.data['caption']

        if updated_caption:
            grp = WorkoutGroups.objects.get(id=wid)
            if grp:
                print("Updating caption to: ", updated_caption)
                grp.caption = updated_caption
                grp.save()
                return Response({"data": 'successfully updated caption'})
        return Response({"err": 'Failed to update caption'})

    @ action(detail=False, methods=['POST'], permission_classes=[SelfActionPermission])
    def update_for_date(self, request, pk=None):
        wid = request.data['id']
        updated_for_date = request.data['for_date']

        if updated_for_date:
            grp = WorkoutGroups.objects.get(id=wid)
            if grp:
                print("Updating for date to: ", updated_for_date)
                grp.for_date = updated_for_date
                grp.save()
                return Response({"data": 'successfully updated for date'})
        return Response({"err": 'Failed to update for date'})


    @ action(detail=False, methods=['POST'], permission_classes=[])
    def finish(self, request, pk=None):
        try:
            user_id = request.user.id
            workout_group_id = request.data.get("group")
            print(f"Finishing workout group: {workout_group_id=}")
            workout_group = WorkoutGroups.objects.get(id=workout_group_id)
            if not workout_group.workouts_set.exists():
                return Response(to_data(f"Cannot finish workoutgroup without workouts {workout_group_id=}."))
            else:
                # Ensure that at least 1 workout has a workoutItem
                has_items = False
                for workout in workout_group.workouts_set.all():
                    if workout.workoutitems_set.exists() or workout.workoutdualitems_set.exists():
                        has_items = True
                if not has_items:
                    return Response(to_data("Cannot finish workoutgroup without workout items."))

            # Permisson TODO create permission class
            # This shoul be covered byt he permission class already....
            if workout_group.owned_by_class:
                gym_class = GymClasses.objects.get(id=workout_group.owner_id)
                if (not is_gym_class_owner(request.user, gym_class) and
                        not is_gymclass_coach(request.user, gym_class)):
                    return Response({"error": "User is not owner or coach"})
            elif not str(user_id) == str(workout_group.owner_id):
                print("User is not owner")
                return Response({"error": "User is not owner"})

            workout_group.finished = True
            # TODO Also if the user is finishing a template workout, we need
            #     to also check if they completed all the workouts in this template/ temaplte_num
            if workout_group.is_template:
                workout_group.template_finished = True
            workout_group.save()

            return Response(WorkoutGroupsSerializer(workout_group, context={'request': request}).data)
        except Exception as e:
            print("Error finished group workout", e)
            return Response({"error": "Error finished group workout"})

    def destroy(self, request, pk=None):
        workout_group_id = pk
        workout_group = WorkoutGroups.objects.get(id=workout_group_id)
        if workout_group.finished:
            workout_group.archived = True
            # workout_group.date_archived = datetime.now()
            workout_group.date_archived = timezone.now()
            workout_group.save()
            return Response(WorkoutGroupsSerializer(workout_group, context={'request': request}).data)
        workout_group.delete()
        # workout_group.save() # This resavess the object and doesnt dlete it.
        return Response(to_data('Deleted WorkoutGroup'))


    def get_queryset(self):
        '''Affects destroy!'''
        if self.request.method == "DELETE":
            return super().get_queryset()

        # Apply any filtering or ordering here
        queryset = super().get_queryset().order_by('for_date')  # Need to order by rating... and need to add rating
        queryset = queryset[:40]
        return queryset

class WorkoutsViewSet(viewsets.ModelViewSet, DestroyWithPayloadMixin, WorkoutPermission):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = Workouts.objects.all()
    serializer_class = WorkoutSerializer
    permission_classes = [WorkoutPermission]

    def get_serializer_class(self):
        if self.action == 'list' or self.action == 'retrieve':
            return WorkoutSerializer
        if self.action == 'create':
            return WorkoutCreateSerializer
        return WorkoutSerializer


    def create(self, request):
        try:
            workout_group_id = request.data.get('group')

            workout_group = WorkoutGroups.objects.get(id=workout_group_id)
            if workout_group.finished:
                return Response({'error': 'Workout already finsined'})

            data = {**request.data.dict(), 'group_id': workout_group_id}
            del data['group']

            print('Workout data:', data)
            workout, new_or_nah = Workouts.objects.get_or_create(**data)
            # if not new_or_nah:
            #     return Response(to_err("Workout with this data already exists."))

            return Response(WorkoutCreateSerializer(workout).data)
        except Exception as err:
            print(f"Error creating Workout: ", err)
            return Response(to_err(str(err), err))



    def update(self, request, *args, **kwargs):
        print(f"PUT Update: {args=} {kwargs=}")
        try:
            # Partially update or fully update depending on whether it is a PUT or PATCH request
            partial = kwargs.pop('partial', False)
            workout = self.get_object()

            # Pass the request data to the serializer
            serializer = self.get_serializer(workout, data=request.data, partial=partial)

            print(f"update: {request.data=}")

            # Check if the data is valid
            if serializer.is_valid():
                # Save the updated instance
                serializer.save()
                return Response(serializer.data)
            else:
                # Return a response with an error if the data is invalid
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as err:
            print(f"Update Workout error: {err=}")
        return Response({'detail': "Update Workout error"})

    # Only need this if we inlcude CompletedWorkouts
    # def retrieve(self, request, *args, **kwargs):
    #     # workout_id = request.data.get('id')
    #     workout_id = kwargs.get('pk')
    #     print("Custom retrieve for workout! need completed workouts as well....")
    #     try:
    #         workout = Workouts.objects.get(id=workout_id)
    #     except Exception as err:
    #         print(f"Error getting workout by id: {err=}")
    #     return Response(WorkoutSerializer(workout).data)



    def destroy(self, request, pk=None):
        workout_id = pk
        workout = Workouts.objects.get(id=workout_id)
        print(f"Destroying wod from group {workout.group.finished=}")
        if workout.group.finished:
            return Response(to_err("Cannot remove workouts from finished workout group."), status=403)

        workout.delete()
        return Response(WorkoutSerializer(workout).data)

# // Not used
def NoDefaultBehavior(cls):

    '''
        Used to avoid default behavior on Viewset routes. A simple View could have been used, in hindsight.
        But to avoid reconfiguring the router, I would prefer to just shut down the default routes for now.
        For example: WorkoutItems are not created one request at a time, instead they are created all in one request.
        - we create an endpoint, items, which takes the data and perfroms the task.
        - So we want to use the same Structure in our project but for security, we do not want to allow access to the default endpoints.
        - We do not want a user to send a request to the server to create a single workout for an item or delete them.

        - Also, I dont want to bloat the permission classes to filter out requests for these endpoints.


        This is a poor solution....
    '''

    def list(self, request):
        return Response(to_err("route not available", Exception()), status=404)

    def create(self, request):
        return Response(to_err("route not available", Exception()), status=409)

    def retrieve(self, request, pk=None):
        return Response(to_err("route not available", Exception()), status=404)

    def update(self, request, pk=None):
        return Response(to_err("route not available", Exception()), status=404)

    def partial_update(self, request, pk=None):
        return Response(to_err("route not available", Exception()), status=404)

    def destroy(self, request, pk=None):
        return Response(to_err("route not available", Exception()), status=404)

    if getattr(cls, 'list').__qualname__ == "CreateModelMixin.list":
        setattr(cls, 'list', list)
    if getattr(cls, 'create').__qualname__ == "CreateModelMixin.create":
        setattr(cls, 'create', create)
    if getattr(cls, 'retrieve').__qualname__ == "CreateModelMixin.retrieve":
        setattr(cls, 'retrieve', retrieve)
    if getattr(cls, 'update').__qualname__ == "CreateModelMixin.update":
        setattr(cls, 'update', update)
    if getattr(cls, 'partial_update').__qualname__ == "CreateModelMixin.partial_update":
        setattr(cls, 'partial_update', partial_update)
    if getattr(cls, 'destroy').__qualname__ == "CreateModelMixin.destroy":
        setattr(cls, 'destroy', destroy)
    return cls


class WorkoutItemsViewSet(viewsets.ModelViewSet,  WorkoutItemsPermission ):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = WorkoutItems.objects.all()
    permission_classes=[WorkoutItemsPermission]


    def create(self, request, *args, **kwargs):
        # return super().create(request, *args, **kwargs)
        return Response(to_err("Failed, route not available.", Exception()), status=404)

    @ action(detail=False, methods=['post'], permission_classes=[WorkoutItemsPermission])
    def update_items(self, request, pk=None):
        try:
            workout_id = request.data.get("workout", 0)
            print("Updating items fpr workout ID: ", workout_id)
            with transaction.atomic():
                WorkoutItems.objects.filter(workout__id=workout_id).delete()
                return self.create_items(request)

        except Exception as e:
            print("Error update_items: ", e)
            return Response(to_err("Failed to update items"))


    def create_items(self, request):
        try:
            print("Creating workout items: ", request.data)
            workout_items = json.loads(request.data.get("items", '[]'))
            workout_id = request.data.get("workout", 0)
            workout = Workouts.objects.get(id=workout_id)


            names = request.data.get('names')
            tags = request.data.get('tags')

            if isinstance(names, str):
                names = json.loads(names)
            if isinstance(tags, str):
                tags = json.loads(tags)


            if not workout:
                # TODO() Throw error?
                return Response(to_data("Workout not found"))

            print('Items', workout_items)
            print('Workout ID:', workout_id)

            items = []
            for w in workout_items:
                try:
                    del w['id']
                    del w['workout']
                except Exception as err:
                    # print("Nothing to delete")
                    pass
                print(f"{w=}")
                items.append(WorkoutItems(
                    **{**w, "workout": Workouts(id=workout_id), "name": WorkoutNames(id=w['name']['id'])}))
            created_workout_items = WorkoutItems.objects.bulk_create(items)

            wStats, mewly_created = WorkoutStats.objects.get_or_create(workout_id=workout.id)
            wStats.tags = tags
            wStats.items = names
            wStats.save()
            print("Created stats: ", wStats)

            return Response(WorkoutItemSerializer(created_workout_items, many=True).data)
        except Exception as e:
            print("create_items err: ", e)
            return Response(to_err("Failed to insert"), e)



    @ action(detail=False, methods=['post'], permission_classes=[WorkoutItemsPermission])
    def items(self, request, pk=None):
       return self.create_items(request)


    def get_serializer_class(self):
        if self.action == 'list' or self.action == 'retrieve':
            return WorkoutItemSerializer
        if self.action == 'create':
            return WorkoutItemCreateSerializer
        return WorkoutItemSerializer


class WorkoutDualItemsViewSet(viewsets.ModelViewSet,  WorkoutItemsPermission ):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = WorkoutDualItems.objects.all()
    permission_classes=[WorkoutDualItemsPermission]


    def create(self, request, *args, **kwargs):
        # return super().create(request, *args, **kwargs)
        return Response(to_err("Failed, route not available.", Exception()), status=404)


    def createDualItems(self, request):
        try:
            print("Creating workout Dual Items: ", request.data)
            workout_items = json.loads(request.data.get("items", '[]'))
            workout_id = request.data.get("workout", 0)
            workout = Workouts.objects.get(id=workout_id)


            names = request.data.get('names')
            tags = request.data.get('tags')

            if isinstance(names, str):
                names = json.loads(names)
            if isinstance(tags, str):
                tags = json.loads(tags)

            if not workout:
                # TODO() Throw error?
                return Response(to_err("Workout not found"))

            print('Dual Items', workout_items)
            print('Workout ID for DualItems:', workout_id)

            items = []
            for w in workout_items:
                del w['id']
                del w['workout']
                items.append(WorkoutDualItems(
                    **{**w, "workout": Workouts(id=workout_id), "name": WorkoutNames(id=w['name']['id'])}))

            wStats, mewly_created = WorkoutStats.objects.get_or_create(workout_id=workout.id)
            wStats.tags = tags
            wStats.items = names
            wStats.save()
            print("Created stats: ", wStats)

            return Response(WorkoutDualItemSerializer(WorkoutDualItems.objects.bulk_create(items), many=True).data)
        except Exception as e:
            print(e)
            return Response(to_err("Failed to insert"))


    @action(detail=False, methods=['post'], permission_classes=[WorkoutDualItemsPermission])
    def update_items(self, request, pk=None):
        try:

            workout_id = request.data.get("workout", 0)
            with transaction.atomic():
                WorkoutDualItems.objects.filter(workout__id=workout_id).delete()
                return self.createDualItems(request)

        except Exception as err:
            return Response(to_err("Failed to update dual items"), err)



    @action(detail=False, methods=['post'], permission_classes=[WorkoutDualItemsPermission])
    def items(self, request, pk=None):
        return self.createDualItems(request)

    @ action(detail=False, methods=['post'], permission_classes=[WorkoutDualItemsPermission])
    def record_items(self, request, pk=None):
        '''Updates items once the workout is completed.'''
        try:
            print("Updating workout Dual Items: ", request.data)
            workout_items = json.loads(request.data.get("items", '[]'))
            workout_id = request.data.get("workout", 0)
            workout = Workouts.objects.get(id=workout_id)

            if not workout:
                # TODO() Throw error?
                return Response(to_err("Workout not found"))

            print('Dual Items', workout_items)
            print('Workout ID for DualItems:', workout_id)

            items = []
            for w in workout_items:
                del w['workout']
                nw = WorkoutDualItems(
                    **{**w, "finished": True, "workout": Workouts(id=workout_id), "name": WorkoutNames(id=w['name']['id'])})
                nw.save()
                items.append(nw)

            return Response(WorkoutDualItemSerializer(items, many=True).data)
        except Exception as e:
            print("Error updating dual items: ", e)
            raise e
            # return Response(to_err("Failed to insert"))



    def get_serializer_class(self):
        if self.action == 'list' or self.action == 'retrieve':
            return WorkoutDualItemSerializer
        if self.action == 'create':
            return WorkoutDualItemCreateSerializer
        return WorkoutDualItemSerializer



########################################################
#   ////////////////////////////////////////////////   #
########################################################

class CompletedWorkoutGroupsViewSet(DestroyWithPayloadMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = CompletedWorkoutGroups.objects.all()
    serializer_class = CompletedWorkoutGroupsSerializer
    permission_classes = [CompletedWorkoutGroupsPermission]

    def create_items(self, request, workout_items, completed_workout_id):
        allItems = []
        for item in workout_items:
            _item = {**item}
            name = _item['name']
            del _item['date']
            del _item['name']
            del _item['id']
            del _item['workout']
            _item['user_id'] = request.user.id
            _item['completed_workout'] = completed_workout_id

            allItems.append(
                CompletedWorkoutItems(
                    **{
                        **_item,
                        "completed_workout": CompletedWorkouts(id=completed_workout_id),
                        "name": WorkoutNames(id=name['id']),
                        'user_id': request.user.id
                    }
                )
            )
        return allItems

    def record_dualitems(self, request, workout_items, completed_workout_id):
        allItems = []
        for item in workout_items:
            _item = {**item}
            name = _item['name']
            del _item['date']
            del _item['name']
            del _item['id']
            del _item['workout']
            _item['user_id'] = request.user.id
            _item['completed_workout'] = completed_workout_id

            allItems.append(
                CompletedWorkoutDualItems(
                    **{
                        **_item,
                        "completed_workout": CompletedWorkouts(id=completed_workout_id),
                        "name": WorkoutNames(id=name['id']),
                        'user_id': request.user.id,
                    }
                )
            )
        return allItems


    def create(self, request):
        ''' Create a completed workout group w/ media, workouts and workout items.
            1. CreateCWG
            2. Upload Media
            3. Create Cwrokouts w/ their CompleteItems

            if step 2 fails, media is not uploaded successfully,
                - delete CWG and return
        '''
        comp_workout_group = None
        data = {**request.data.dict()}
        files = request.data.getlist("files", [])
        workout_group_id = data['workout_group']
        title = data['title']
        caption = data['caption']
        workouts = json.loads(data['workouts'])
        if 'files' in data:
            del data['files']
        if 'workouts' in data:
            del data['workouts']
        if 'workout_group' in data:
            del data['workout_group']

        try:
            workout_group = WorkoutGroups.objects.get(id=workout_group_id)
            if not workout_group.finished:
                return Response(to_err("Cannot create completedWorkoutGroup for a non finished WorkoutGroup"))

            comp_workout_group, newly_created = CompletedWorkoutGroups.objects.get_or_create(
                **{**data, 'caption': caption, 'media_ids': [], 'workout_group_id': workout_group_id, 'user_id': request.user.id})
            if not newly_created:
                return Response(to_err("Workout already create. Must delete and reupload w/ media or edit workout."))

        except Exception as e:
            print("Error creating CompletedWorkoutGroup:", e)
            if comp_workout_group:
                comp_workout_group.delete()
            return Response(to_err("Failed to create CompletedWorkoutGroup", e), status=422)

        uploaded_names = []
        parent_id = comp_workout_group.id
        # try:
        #     parent_id = comp_workout_group.id
        #     print("Uploading files for completedWorkoutGroup: ", files, "\n")
        #     uploaded_names = upload_media(
        #         files, parent_id, FILES_KINDS[COMP_WORKOUT_FILES])

        #     # If given files to do match uploaded files, consider bad upload, delete created stuff and return error
        #     # if len(files) != len(uploaded_names):
        #     #     comp_workout_group.delete() #
        #     #     delete_media(parent_id, uploaded_names, FILES_KINDS[COMP_WORKOUT_FILES]) # undo step two
        #     #     return Response(to_err("Failed to upload media files."))

        #     comp_workout_group.media_ids = json.dumps(
        #         [n for n in uploaded_names])
        #     comp_workout_group.save()

        # except Exception as e:
        #     comp_workout_group.delete()  # undo step one
        #     delete_media(parent_id, uploaded_names,
        #                  FILES_KINDS[COMP_WORKOUT_FILES])  # undo step two
        #     print("Error uploading media:", e)
        #     return Response(to_err("Error uploading media"))


        # A list of item will come in that are Normal or Dual
        #
        try:
            allItems = []
            allDualItems = []
            for w in workouts:
                _w = {**w}
                print("Workout to add as completed", w)
                workout_items = _w['workout_items']
                workout_id = _w['id']
                del _w['id']
                del _w['workout_items']
                del _w['date']
                del _w['group']

                completed_workout, newly_created = CompletedWorkouts.objects.get_or_create(**{
                    **_w,
                    'user_id': request.user.id,
                    'completed_workout_group_id': parent_id,
                    'workout_id': workout_id
                })


                # Depending on the workout scheme type, we will have regular items
                # Or we will have dual items.
                if _w["scheme_type"] <= 2:
                    print("Attempt create items")
                    allItems.extend(self.create_items( request, workout_items, completed_workout.id))
                else:
                    print("Attempt create dual items")
                    allDualItems.extend(self.record_dualitems( request, workout_items, completed_workout.id))

            CompletedWorkoutItems.objects.bulk_create(allItems)
            CompletedWorkoutDualItems.objects.bulk_create(allDualItems)

        except Exception as e:
            comp_workout_group.delete()  # undo step one, should delete all foregin keys
            # delete_media(parent_id, uploaded_names,
            #              FILES_KINDS[COMP_WORKOUT_FILES])  # undo step two
            msg = f"Error creating CompleteWorkoutItems {e}"
            print(msg, e)
            return Response(to_err(msg))

        return Response(CompletedWorkoutGroupsSerializer(comp_workout_group).data)

    def last_id_from_media(self, cur_media_ids: List[str]) -> int:
        last_id = 0
        if not cur_media_ids:
            return last_id

        # Items shoudl remain in order but we will ensure by sorting.
        # This should have little impact when limiting each workout to 5-7 posts.
        media_ids = sorted(cur_media_ids, key=lambda p: p.split(".")[0])
        last_media_id = media_ids[-1]
        return int(last_media_id.split(".")[0])

    @action(detail=True, methods=['post'], permission_classes=[EditWorkoutMediaPermission])
    def add_media_to_workout(self, request, pk=None):
        # try:
        workout_group_id = pk
        files = request.data.getlist("files")

        workout_group = CompletedWorkoutGroups.objects.get(id=workout_group_id)
        cur_media_ids = sorted(json.loads(workout_group.media_ids))

        last_id = self.last_id_from_media(cur_media_ids)

        print("Last id: ", last_id)
        uploaded_names = upload_media(
            files, workout_group.id, FILES_KINDS[COMP_WORKOUT_FILES], start=last_id + 1)
        print("Num uploaded: ", uploaded_names)

        print("Cur media ids: ", cur_media_ids)
        cur_media_ids.extend(uploaded_names)

        print("Updated Cur media ids: ", cur_media_ids)
        workout_group.media_ids = json.dumps(cur_media_ids)
        workout_group.save()
        return Response(to_data("Successfully added media to workout"))

        # except Exception as e:
        #     print(e)
        #     return Response("Failed to add media to workout")

    @action(detail=True, methods=['delete'], permission_classes=[EditWorkoutMediaPermission])
    def remove_media_from_workout(self, request, pk=None):
        try:
            workout_group_id = pk
            remove_media_ids = json.loads(request.data.get("media_ids"))
            workout_group = CompletedWorkoutGroups.objects.get(
                id=workout_group_id)
            cur_media_ids = sorted(json.loads(workout_group.media_ids))
            deleted_ids = delete_media(
                workout_group.id, remove_media_ids, FILES_KINDS[COMP_WORKOUT_FILES])

            cur_media_ids = list(
                filter(lambda n: not str(n) in deleted_ids, cur_media_ids))
            print("Filtered Current media ids: ", cur_media_ids)
            workout_group.media_ids = json.dumps(cur_media_ids)
            workout_group.save()
            return Response(to_data("Deleted"))
        except Exception as e:
            print(e)
            return Response(to_err("Failed to remove media"))

    @action(detail=False, methods=['get'], permission_classes=[])
    def workouts(self, request, pk=None):
        try:
            owner_id = request.user.id
            workout_groups: CompletedWorkoutGroups = CompletedWorkoutGroups.objects.filter(
                owner_id=owner_id)
            # // Workout group is single group with multiple workouts
            return Response(CompletedWorkoutGroupsSerializer(workout_groups).data)
        except Exception as e:
            print(e)
            return Response(to_err("Failed get user's workouts."))

    @action(detail=True, methods=['get'], permission_classes=[])
    def completed_workout_group(self, request, pk=None):
        try:
            workout_groups: CompletedWorkoutGroups = CompletedWorkoutGroups.objects.get(
                id=pk)
            # // Workout group is single group with multiple workouts
            return Response(CompletedWorkoutGroupsSerializer(workout_groups).data)
        except Exception as e:
            print(e)
            return Response(to_err("Failed get user's completed_workout_group."))

    @action(detail=True, methods=['get'], permission_classes=[])
    def completed_workout_group_by_og_workout_group(self, request, pk=None):
        og_workout_group_id = pk
        complete_workout_groups = CompletedWorkoutGroups.objects.filter(
            user_id=request.user.id,
            workout_group_id=og_workout_group_id
        )
        complete_workout_group = None if len(
            complete_workout_groups) == 0 else complete_workout_groups[0]

        print("completed_workout_group_by_og_workout_group")
        return Response(CompletedWorkoutGroupsSerializer(complete_workout_group).data)

    def update(self, request, *args, **kwargs):
        # return super().create(request, *args, **kwargs)
        return Response(to_err("Failed, route not available.", Exception()), status=404)
    def partial_update(self, request, *args, **kwargs):
        # return super().create(request, *args, **kwargs)
        return Response(to_err("Failed, route not available.", Exception()), status=404)



    def get_serializer_class(self):
        if self.action == 'list' or self.action == 'retrieve':
            return CompletedWorkoutGroupsSerializer
        if self.action == 'create':
            return CompletedWorkoutCreateSerializer
        return CompletedWorkoutGroupsSerializer


class CompletedWorkoutsViewSet(DestroyWithPayloadMixin, viewsets.ModelViewSet):
    queryset = CompletedWorkouts.objects.all()
    serializer_class = CompletedWorkoutSerializer
    permission_classes = [CompletedWorkoutsPermission]

    def create(self, request, *args, **kwargs):
        # return super().create(request, *args, **kwargs)
        return Response(to_err("Failed, route not available.", Exception()), status=404)
    def update(self, request, *args, **kwargs):
        # return super().create(request, *args, **kwargs)
        return Response(to_err("Failed, route not available.", Exception()), status=404)
    def partial_update(self, request, *args, **kwargs):
        # return super().create(request, *args, **kwargs)
        return Response(to_err("Failed, route not available.", Exception()), status=404)
    def destroy(self, request, *args, **kwargs):
        # return super().create(request, *args, **kwargs)
        return Response(to_err("Failed, route not available.", Exception()), status=404)

########################################################
#   ////////////////////////////////////////////////   #
########################################################



########################################################
#   ////////////////////////////////////////////////   #
########################################################


class WorkoutNamesViewSet(viewsets.ModelViewSet, SuperUserWritePermission):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = WorkoutNames.objects.all()
    serializer_class = WorkoutNamesSerializer
    permission_classes=[SuperUserWritePermission]

    def create(self, request):
        # try:

        data = request.data.copy().dict()
        files = request.data.getlist("files", [])
        categories = json.loads(data['categories'])
        primary = data['primary']
        secondary = data['secondary']
        del data['files']
        del data['categories']
        del data['primary']
        del data['secondary']

        # Models expects True/ False, coming from json, we get true/ false. Instead we store 0,1 and convert

        # TODO Add workoutCategories.
        workoutCategories = WorkoutCategories.objects.filter(id__in=categories)
        if primary:
            data['primary'] = WorkoutCategories.objects.get(id=primary)
        if secondary:
            data['secondary'] = WorkoutCategories.objects.get(id=secondary)

        workout_name, newly_created = WorkoutNames.objects.get_or_create(
            **{
                **data,
                'media_ids': [],
            })

        if not newly_created:
            return Response(to_data("Workout name already created. Must delete and reupload w/ media or edit workout name."))

        [workout_name.categories.add(c) for c in workoutCategories]
        workout_name.save()

        parent_id = workout_name.id
        uploaded_names = upload_media(
            files, parent_id, FILES_KINDS[NAME_FILES])
        workout_name.media_ids = json.dumps([n for n in uploaded_names])
        workout_name.save()

        return Response(WorkoutNamesSerializer(workout_name).data)
        # except Exception as e:
        #     print(e)
        #     return Response("Failed to create workout")

    @action(detail=True, methods=['post'], permission_classes=[])
    def add_media_to_workout_name(self, request, pk=None):
        # try:
        workout_id = pk
        files = request.data.getlist("files")

        workout = WorkoutNames.objects.get(id=workout_id)
        cur_media_ids = sorted(json.loads(workout.media_ids))

        last_id = self.last_id_from_media(cur_media_ids)

        print("Last id: ", last_id)
        uploaded_names = upload_media(
            files, workout.id, FILES_KINDS[NAME_FILES], start=last_id + 1)
        print("Num uploaded: ", uploaded_names)

        print("Cur media ids: ", cur_media_ids)
        cur_media_ids.extend(uploaded_names)

        print("Updated Cur media ids: ", cur_media_ids)
        workout.media_ids = json.dumps(cur_media_ids)
        workout.save()
        return Response(to_data("Successfully added media to workout"))

        # except Exception as e:
        #     print(e)
        #     return Response("Failed to add media to workout")

    @action(detail=True, methods=['delete'], permission_classes=[])
    def remove_media_from_workout_name(self, request, pk=None):
        try:
            workout_id = pk
            remove_media_ids = json.loads(request.data.get("media_ids"))
            workout = WorkoutNames.objects.get(id=workout_id)
            cur_media_ids = sorted(json.loads(workout.media_ids))
            deleted_ids = delete_media(
                workout.id, remove_media_ids, FILES_KINDS[NAME_FILES])

            cur_media_ids = list(
                filter(lambda n: not str(n) in deleted_ids, cur_media_ids))
            print("Filtered Current media ids: ", cur_media_ids)
            workout.media_ids = json.dumps(cur_media_ids)
            workout.save()
            return Response(to_data("Deleted"))
        except Exception as e:
            print(e)
            return Response(to_err("Failed to remove media"))

class WorkoutCategoriesViewSet(viewsets.ModelViewSet, SuperUserWritePermission):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = WorkoutNames.objects.all()
    serializer_class = WorkoutCategorySerializer
    permission_classes=[SuperUserWritePermission]


class CoachesViewSet(viewsets.ModelViewSet, CoachPermission):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = Coaches.objects.all()
    permission_classes = [CoachPermission]

    @ action(detail=True, methods=['GET'])
    def coaches(self, request, pk=None):
        '''Gets all coaches for a class. '''
        coaches: List[Coaches] = Coaches.objects.filter(gym_class__id=pk)
        ids = [c.user_id for c in coaches]
        print("Coach ids: ", ids)

        users = User.objects.filter(id__in=ids)
        # return Response(CoachesSerializer(coaches, many=True).data)
        return Response(UserWithoutEmailSerializer(users, many=True).data)

    @ action(detail=False, methods=['DELETE'])
    def remove(self, request, pk=None):
        try:
            remove_user_id = request.data.get("user_id", "0")
            gym_class_id = request.data.get("gym_class", "0")
            coach = Coaches.objects.get(
                user_id=remove_user_id, gym_class__id=gym_class_id)
            coach.delete()
            return Response(to_data(CoachesSerializer(coach).data))
        except Exception as e:
            print(e)

        return Response(to_err("Failed to remove coach"))

    def update(self, request, *args, **kwargs):
        # return super().create(request, *args, **kwargs)
        return Response(to_err("Failed, route not available.", Exception()), status=404)
    def partial_update(self, request, *args, **kwargs):
        # return super().create(request, *args, **kwargs)
        return Response(to_err("Failed, route not available.", Exception()), status=404)
    def destroy(self, request, *args, **kwargs):
        # return super().create(request, *args, **kwargs)
        return Response(to_err("Failed, route not available.", Exception()), status=404)


    def get_serializer_class(self):
        if self.action == 'list' or self.action == 'retrieve':
            return CoachesSerializer
        if self.action == 'create':
            return CoachesCreateSerializer
        return CoachesSerializer


class ClassMembersViewSet(viewsets.ModelViewSet, MemberPermission):
    """
    API endpoint that allows users to be viewed or edited.
    Permissions:

    """
    queryset = ClassMembers.objects.all()
    permission_classes = [MemberPermission]

    @ action(detail=True, methods=['GET'])
    def members(self, request, pk=None):
        '''Gets all members for a class. '''
        members: List[ClassMembers] = ClassMembers.objects.filter(
            gym_class__id=pk)
        ids = [c.user_id for c in members]
        print("Coach ids: ", ids)

        users = User.objects.filter(id__in=ids)
        # return Response(CoachesSerializer(coaches, many=True).data)
        return Response(UserWithoutEmailSerializer(users, many=True).data)

    @ action(detail=False, methods=['DELETE'])
    def remove(self, request, pk=None):
        try:
            remove_user_id = request.data.get("user_id", "0")
            gym_class_id = request.data.get("gym_class", "0")
            class_member = ClassMembers.objects.get(
                user_id=remove_user_id, gym_class__id=gym_class_id)
            class_member.delete()
        except Exception as e:
            print(e)
            return Response(to_err("Failed to remove class member"))

        return Response(to_data("Deleted"))

    def update(self, request, *args, **kwargs):
        # return super().create(request, *args, **kwargs)
        return Response(to_err("Failed, route not available.", Exception()), status=404)
    def partial_update(self, request, *args, **kwargs):
        # return super().create(request, *args, **kwargs)
        return Response(to_err("Failed, route not available.", Exception()), status=404)
    def destroy(self, request, *args, **kwargs):
        # return super().create(request, *args, **kwargs)
        return Response(to_err("Failed, route not available.", Exception()), status=404)


    def get_serializer_class(self):
        if self.action == 'list' or self.action == 'retrieve':
            return ClassMembersSerializer
        if self.action == 'create':
            return ClassMembersCreateSerializer
        return ClassMembersSerializer


class WorkoutMaxViewSet(viewsets.ModelViewSet):
    """ViewSet for handling workout maxes"""
    permission_classes = [SelfActionPermission]

    def get_serializer_class(self):
        if self.action == 'history':
            return UserWorkoutMaxHistorySerializer
        elif self.action == 'list_workouts':
            return WorkoutNameMaxSerializer
        return UserWorkoutMaxSerializer

    def get_queryset(self):
        """Return maxes for the current user only"""
        if self.action == 'history':
            return UserWorkoutMaxHistory.objects.filter(
                user=self.request.user
            ).order_by('-recorded_date')
        return UserWorkoutMax.objects.filter(
            user=self.request.user
        ).order_by('workout_item__name')

    def perform_create(self, serializer):
        """Set the user when creating a new max record"""
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['GET'])
    def list_workouts(self, request):
        """List all workout items with their current max values for the user"""
        workout_names = WorkoutNames.objects.all()
        serializer = self.get_serializer(workout_names, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['GET'])
    def history(self, request, pk=None):
        """Get history for a specific workout item max"""
        try:
            workout_name = WorkoutNames.objects.get(pk=pk)
            history = UserWorkoutMaxHistory.objects.filter(
                user_id=request.user.id,
                workout_name=workout_name
            ).order_by('-recorded_date')

            serializer = self.get_serializer(history, many=True)
            return Response(serializer.data)
        except WorkoutItems.DoesNotExist:
            return Response(
                {'error': 'Workout item not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['POST'])
    def update_max(self, request):
        """Update a user's max for a workout item and record in history"""
        print("Update_max: ", request.data.keys(), )
        workout_name_id = request.data.get('workout_name_id')

        max_value = request.data.get('max_value')
        unit = request.data.get('unit', 'kg')  # Default to kg if not specified
        notes = request.data.get('notes', '')


        if not workout_name_id or max_value is None:
            print("{'error': 'workout_name_id and max_value are required'},")
            return Response(
                {'error': 'workout_name_id and max_value are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            max_value = float(max_value)
        except ValueError:
            print("{'error': 'max_value must be a number'},")
            return Response(
                {'error': 'max_value must be a number'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            workout_name = WorkoutNames.objects.get(id=workout_name_id)
        except WorkoutItems.DoesNotExist:
            print("{'error': 'Workout item not found'} id: ", workout_name_id)
            return Response(
                {'error': 'Workout item not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # 1. Update or create the current max record
        current_max, created = UserWorkoutMax.objects.update_or_create(
            user_id=request.user.id,
            workout_name=workout_name,
            defaults={
                'max_value': max_value,
                'unit': unit,
                'notes': notes
            }
        )

        # 2. Add to history log
        history_record = UserWorkoutMaxHistory.objects.create(
            user_id=request.user.id,
            workout_name=workout_name,
            max_value=max_value,
            unit=unit,
            notes=notes,

        )

        res = {
            'current_max': UserWorkoutMaxSerializer(current_max).data,
            'history_record': UserWorkoutMaxHistorySerializer(history_record).data
        }
        print("Update_max res: ", res)

        return Response(res)

    @action(detail=True, methods=['GET'])
    def progress(self, request, pk=None):
        """Get progress data for a specific workout item"""
        try:
            workout_item = WorkoutItems.objects.get(pk=pk)
            history = UserWorkoutMaxHistory.objects.filter(
                user_id=request.user.id,
                workout_item=workout_item
            ).order_by('recorded_date')

            # Format data for chart display
            progress_data = [{
                'date': record.recorded_date.strftime('%Y-%m-%d'),
                'value': record.max_value,
                'unit': record.unit
            } for record in history]

            return Response(progress_data)
        except WorkoutItems.DoesNotExist:
            return Response(
                {'error': 'Workout item not found'},
                status=status.HTTP_404_NOT_FOUND
            )



# Not used... but could be
class BodyMeasurementsViewSet(viewsets.ModelViewSet, SelfActionPermission):
    """
    API endpoint that allows users to be viewed or edited.
    Permissions:

    """
    queryset = BodyMeasurements.objects.all()
    permission_classes = [SuperUserWritePermission]






class WorkoutGroupPagination(PageNumberPagination):
    # const PAGE_SIZE = 20;
    page_size = 20 # Must Match FrontEnd -> (apps) index.tsx



def count_tokens(text: str, model="gpt-3.5-turbo") -> int:
    enc = tiktoken.encoding_for_model(model)
    return len(enc.encode(text))

def count_message_tokens(messages: list, model="gpt-3.5-turbo") -> int:
    enc = tiktoken.encoding_for_model(model)
    tokens = 0
    for m in messages:
        tokens += 4  # base cost per message (OpenAI rule of thumb)
        tokens += len(enc.encode(m["content"]))
    tokens += 2  # for assistant priming
    return tokens + 2 ## Good measure

def next_template_num(user, template_name):
    # Grab the next latest template number, default is 0, first one created will be 1
    latest_wg_by_template = WorkoutGroups.objects.filter(owner_id=user.id, template_name=template_name).order_by("-template_num").first()
    return latest_wg_by_template.template_num + 1 if latest_wg_by_template else 1

def cur_template_num(user, template_name):
    # First one created will have 1 or larger
    latest_wg_by_template = WorkoutGroups.objects.filter(owner_id=user.id, template_name=template_name).order_by("-template_num").first()
    return latest_wg_by_template.template_num if latest_wg_by_template else 0

class AIViewSet(viewsets.ViewSet):
    @action(detail=False, methods=['POST'], permission_classes=[SelfActionPermission])
    def create_workout(self, request, pk=None):

        quota, newly_created = TokenQuota.objects.get_or_create(user_id=request.user.id)
        prompt = request.data.get('prompt') # Goal
        scheme_type_text = request.data.get('scheme_type_text')
        userMaxes = request.data.get('userMaxes')
        lastWorkoutGroups = request.data.get('lastWorkoutGroups')
        remaining = quota.remaining_tokens

        if not prompt:
            return Response({"error": ' No prompt given'})

        if remaining <= 0:
            return Response({"error": 'Out of tokens'})




        messages=[
            {"role": "system", "content": "You are a helpful super awesome Sports Strength and Conditioning Coach, your athlete needs a tailored workout plan that will map to their workout app so only structure output in json."},
            {"role": "user", "content": f"Workout maxes: {userMaxes}"},
            {"role": "user", "content": f"MyLast Couple of Workouts: {lastWorkoutGroups}"},
            {"role": "user", "content": f"Workout Scheme Style: {scheme_type_text}"},
            {"role": "user", "content": f"User Goal: {prompt}"},
        ]


        input_tokens = count_message_tokens(messages)
        if input_tokens >= remaining:
            return Response({"error": "Token quota exceeded"}, status=403)

        print("Input token: ", input_tokens)
        max_output_tokens = remaining - input_tokens

        if max_output_tokens <= 1500:
            quota.remaining_tokens = 0
            quota.save()
            return Response({"error": 'Not enough tokens left'})

        response = client.chat.completions.create(
            model="gpt-4o-mini",  # or "gpt-4" if you have access
            # model="gpt-3.5-turbo",  # or "gpt-4" if you have access
            temperature=0.7,
            messages=messages,
            max_tokens=min(16_384, max_output_tokens),
            tools=tools,
            tool_choice="auto",
        )

        input_tokens_used = response.usage.prompt_tokens
        output_tokens_used = response.usage.completion_tokens
        total_tokens = response.usage.total_tokens


        quota.use_tokens(total_tokens)
        print(f"Tokens used this request: {input_tokens_used} ({input_tokens}) + {output_tokens_used} = {total_tokens} ")
        print(f"Token Usage: {quota.remaining_tokens}/1,750,000")

        tool_call = response.choices[0].message.tool_calls[0]
        arguments = json.loads(tool_call.function.arguments)
        print(f"{arguments=}")
        return Response({'data': arguments})

class ProfileViewSet(viewsets.ViewSet):

    @ action(detail=False, methods=['GET'], permission_classes=[])
    def profile(self, request, pk=None):
        print(request.user)
        user_id = request.user.id
        # Need to gather
        # User info
        # Workouts created by user, FUTURE workouts completed by user.
        # Summary of workout load
        profile_data = dict()
        profile_data['user'] = request.user
        user_id = request.user.id
        profile_data['measurements'] = BodyMeasurements.objects.filter(
            user_id=user_id)
        profile_data['membership_on'] = True # Used to control if the app should respect membership features in regards to showing ads since they are test ads.

        return Response(ProfileSerializer(profile_data,  context={'request': request, }).data)

    @action(detail=False, methods=['GET'], permission_classes=[])
    def gym_favs(self, request, pk=None):

        data = dict()
        user_id = request.user.id
        data['favorite_gyms'] = GymFavorites.objects.filter(
            user_id=user_id)
        return Response(ProfileGymFavoritesSerializer(data,  context={'request': request, }).data)

    @action(detail=False, methods=['GET'], permission_classes=[])
    def gym_class_favs(self, request, pk=None):
        data = dict()
        user_id = request.user.id
        data['favorite_gym_classes'] = GymClassFavorites.objects.filter(
            user_id=user_id)
        return Response(ProfileGymClassFavoritesSerializer(data,  context={'request': request, }).data)

    @action(detail=False, methods=['GET'], permission_classes=[SelfActionPermission])
    def workout_group_query(self, request, pk=None):
        query = request.query_params.get("query")
        user_id = request.query_params.get("user_id")

        print(f"Userid : {user_id} WG Query: {query}")

        # results =  WorkoutGroups.objects.annotate(
        #     similarity=TrigramSimilarity('title', query)
        # ).filter(
        #     similarity__gt=0.2,
        #     owner_id=user_id
        # ).order_by('-similarity')


        results = (
            WorkoutGroups.objects
            .filter(owner_id=user_id)
            .annotate(
                title_similarity=TrigramSimilarity('title', query),
                sub_similarity=Max(TrigramSimilarity('workouts__title', query)),  # Trigram against all related workout titles
            )
            .annotate(similarity=Greatest('title_similarity', 'sub_similarity'))
            .filter(similarity__gt=0.2)
            .order_by('-similarity')
            .distinct()
        )


        return Response(WorkoutGroupsSerializer(results, many=True, context={"request": request}).data)



    @action(detail=False, methods=['GET'], permission_classes=[])
    def template_workout_groups(self, request, pk=None):
        user_id = request.user.id
        template_name = request.query_params.get('template_name')
        template_num = cur_template_num(request.user, template_name)
        print("Getting template groups for num: ", template_num)
        # Fetch both workout groups
        wgs = WorkoutGroups.objects.filter(
            owner_id=user_id,
            owned_by_class=False,
            archived=False,  # This essentially means deleted, deleted=False
            template_name=template_name,
            template_num=template_num,
        ).exclude(
            is_template=False
        ).order_by('for_date')

        # IF excluding all finished results in no items, so be it, we are done...
        unfinished_groups = wgs.exclude(template_finished=True)
        num_unfinished_groups = len(wgs.exclude(template_finished=True))

        if num_unfinished_groups == 0:
            return Response(WorkoutGroupsAutoCompletedSerializer(unfinished_groups, many=True, context={'request': request}).data)


        return Response(WorkoutGroupsAutoCompletedSerializer(wgs, many=True, context={'request': request}).data)


    @action(detail=False, methods=['GET'], permission_classes=[])
    def workout_groups(self, request, pk=None):
        user_id = request.user.id
        workouts = dict()
        data = dict()

        # Fetch both workout groups
        wgs = WorkoutGroups.objects.filter(
            owner_id=user_id,
            owned_by_class=False,
            archived=False
        ).exclude(
            finished=False,
            is_template=True
        ).order_by('-for_date')

        cwgs = CompletedWorkoutGroups.objects.filter(
            user_id=user_id).order_by('-for_date')

        # Combine both querysets into a dict
        data = {
            'created_workout_groups': wgs,
            'completed_workout_groups': cwgs
        }

        # Use the combined data in the serializer
        combined_data = CombinedWorkoutGroupsSerializerNoWorkouts(data, context={'request': request}).data

        # Paginate the combined result
        paginator = WorkoutGroupPagination()
        paginated_combined_data = paginator.paginate_queryset(combined_data['created_workout_groups'] + combined_data['completed_workout_groups'], request)
        # print(f"Paginated data: ", paginated_combined_data)
        # Return the paginated response
        return paginator.get_paginated_response(paginated_combined_data)


class BulkTemplateViewSet(viewsets.ViewSet):
    """
    POST /bulktemplates/
    {
      "template": [
        {
          "group": { …WorkoutGroupsViewSet.create payload… },
          "workouts": [
            {
              "workout": { …WorkoutsViewSet.create payload… },
              "items": [ …WorkoutItem objects… ]
            },
            …
          ]
        },
        …
      ]
    }
    """

    @action(detail=False, methods=['POST'], permission_classes=[SelfActionPermission])
    def reset_template(self, request):
        '''  To reset a template  is to simply delete the workoutGroups that werent marked finished. We can ust remove these   '''
        try:
            user = request.user
            template_name = request.data['template_name']



            template_wg = WorkoutGroups.objects.filter(
                is_template=True,
                owner_id=user.id,
                template_name=template_name,
                finished=False,
                template_num = cur_template_num(user, template_name)
            )


            for w in template_wg:
                w.delete()
            return Response({"data": "Successfully removed un-done/finished templates"})
        except Exception as err:
            print("Failed to reset template: ", request.data, err)
        return Response({"err": "Failed to reset template"})





    @action(detail=False, methods=['POST'], permission_classes=[SelfActionPermission])
    def create_template(self, request):
        # print("Request template: ", request.data)
        print("Request template user: ", request.user)
        factory = APIRequestFactory()
        created_groups = []
        user = request.user
        tz = request.tz


        groups = request.data.get("template", [])
        if len(groups) < 1:
            return Response([])

        template_name = groups[0]["group"]['template_name']
        template_num = next_template_num(request.user, template_name)
        for grp in groups:
            # print("Creating group: ", grp)
            group = {**grp["group"]}  # "is_template": True, "template_name": "5_3_1"

            group['template_num'] = template_num

            group_req = factory.post(
                '/workoutGroups/',
                group,
                format='multipart'
            )

            group_req.tz = tz
            force_authenticate(group_req, user=user)
            group_resp = WorkoutGroupsViewSet.as_view({"post": "create"})(group_req)

            print(f"{group_resp.status_code=}")


            if group_resp.status_code not in (status.HTTP_200_OK, status.HTTP_201_CREATED):
                return group_resp

            group_id = group_resp.data["id"]
            created_groups.append(group_id)

            # 2) Create each workout
            print("Creating workouts for group: ", grp.get("workouts", []))
            for wk in grp.get("workouts", []):
                wk_payload = {**wk["workout"], "group": group_id}
                workout_req = factory.post(
                    '/workouts/',
                    wk_payload,
                    format='multipart'
                )

                force_authenticate(workout_req, user=user)
                workout_req.tz = tz

                wk_resp = WorkoutsViewSet.as_view({"post": "create"})(workout_req)
                if wk_resp.status_code not in (status.HTTP_200_OK, status.HTTP_201_CREATED):
                    return wk_resp


                workout_id = wk_resp.data["id"]

                # 3) Bulk‐create items
                items_payload = {
                    "items": json.dumps( wk["items"]),
                    "workout": workout_id,
                    "workout_group": group_id,
                    "tags": json.dumps(wk['tags']),
                    "names": json.dumps(wk['names']),
                }
                items_req = factory.post(
                    '/workoutItems/items/',
                    items_payload,
                    format='multipart'
                )

                force_authenticate(items_req, user=user)
                items_req.tz = tz
                items_resp = WorkoutItemsViewSet.as_view({"post": "items"})(items_req)
                if items_resp.status_code not in (status.HTTP_200_OK, status.HTTP_201_CREATED):
                    return items_resp

        return Response(
            {"created_groups": created_groups},
            status=status.HTTP_201_CREATED
        )



class StatsViewSet(viewsets.ViewSet):
    '''
     Returns workouts between a range of dates either for a user's workouts or a classes workouts.
    '''
    @ action(detail=True, methods=['GET'], permission_classes=[])
    def user_workouts(self, request, pk=None):
        user_id = pk
        if user_id == "0":
            user_id = request.user.id

        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        data = dict()
        start = tz.localize(datetime.combine(
            datetime.strptime(
                start_date,
                "%Y-%m-%d"
            ),
            time.min
        )).strftime("%Y-%m-%d %H:%M:%S%z").rstrip("0")
        end = tz.localize(datetime.combine(
            datetime.strptime(
                end_date,
                "%Y-%m-%d"
            ),
            time.max
        )).strftime("%Y-%m-%d %H:%M:%S%z").rstrip("0")
        # end = datetime.combine(datetime.strptime(end_date, "%Y-%m-%d"), time.max).strftime("%Y-%m-%d %H:%M:%S")

        print('\n', request.query_params, user_id, start, end, '\n',)
        wgs = WorkoutGroups.objects.filter(
            owned_by_class=False,
            owner_id=user_id,
            archived=False,
            finished=True,
            for_date__gte=start,
            for_date__lte=end,
        )
        cwgs = CompletedWorkoutGroups.objects.filter(
            user_id=user_id,
            for_date__gte= start,
            for_date__lte= end,
        )

        for wg in wgs:
            print(wg.for_date)

        data['created_workout_groups'] = wgs
        data['completed_workout_groups'] = cwgs

        return Response(
            list(chain(
                WorkoutGroupsSerializer(
                    wgs,
                    context={'request': request, },
                    many=True
                ).data,
                CompletedWorkoutGroupsSerializer(
                    cwgs,
                    context={'request': request, },
                    many=True
                ).data
            ))
        )





@transaction.atomic
def delete_user_data(user_id, user_email):
    try:
        # 1. Delete records in GymClassFavorites
        # GymClassFavorites.objects.filter(user_id=user_id).delete()

        # 2. Delete records in GymFavorites
        # GymFavorites.objects.filter(user_id=user_id).delete()

        # 3. Delete records in WorkoutGroups
        # Fetch all WorkoutGroups for the above GymClasses ids and user's personal workoutgroups.
        # gym_class_ids = [str(r) for r in GymClasses.objects.filter(gym__owner_id=user_id).values_list('id', flat=True)]
        # print("GymClass ids: ", type(gym_class_ids[0]), gym_class_ids)

        # combined_filter = Q(owner_id=user_id, owned_by_class=False) | Q(owner_id__in=gym_class_ids, owned_by_class=True)
        combined_filter = Q(owner_id=user_id, owned_by_class=False)
        WorkoutGroups.objects.filter(combined_filter).delete()

        # 4. Delete records in CompletedWorkoutGroups
        # CompletedWorkoutGroups.objects.filter(user_id=user_id).delete()

        # 5. Delete records in ClassMembers
        # ClassMembers.objects.filter(user_id=user_id).delete()

        # 6. Delete records in Coaches
        # Coaches.objects.filter(user_id=user_id).delete()

        # 7. Delete GymClasses where related Gyms have the owner_id matching the user_id
        # GymClasses.objects.filter(gym__owner_id=user_id).delete()

        # 8. Delete Gyms owned by the user
        # Gyms.objects.filter(owner_id=user_id).delete()

        # 8. Delete reset password codes stored
        ResetPasswords.objects.filter(email=user_email).delete()

        # 9. Delete User
        User.objects.filter(id=user_id).delete()
        return True, ""  # Success!
    except IntegrityError as ie:
        # This catches database integrity errors, which might be the most common issue.
        return False, str(ie)
    except Exception as e:
        # Optional: You can catch other exceptions and log or handle them if needed.
        print(f"An error occurred: {e}")
        return False, str(e)


class RemoveAccount(viewsets.ViewSet):
    '''
     Returns workouts between a range of dates either for a user's workouts or a classes workouts.
    '''
    @action(detail=False, methods=['POST'], permission_classes=[])
    def remove(self, request, pk=None):
        try:
            email = request.data['email']
            user = User.objects.get(email=email)
            print("Attempting to remove account and data associated with user: ", user)
            print("Need to think about how to remove an account.... Delete their gyms and classes? Mark them as archived? just dont show on search. Remove all workouts and completed workouts, favorites, coach and members")
            deleted, err = delete_user_data(user.id, user.email)
            if deleted:
                return Response({"success": True, "error": ""})
            return Response({"success": False, "error": err})

        except Exception as e:
            print(f"Failed to remove account: ", e)
            return Response({"success": False, "error": str(e)})

def replace_tz_with_UTC(local_date, user_tz):
    """Replaces the local date with UTC TZ"""

    local_datetime = datetime.combine(local_date, datetime.min.time())
    user_timezone = pytz.timezone(user_tz)
    localized_dt = user_timezone.localize(local_datetime)

    # Convert this to UTC without changing the day, month, or year
    return localized_dt.astimezone(pytz.utc)


class SnapshotViewSet(viewsets.ViewSet):
    '''
     Returns workouts between a range of dates either for a user's workouts or a classes workouts.
    '''
    @action(detail=False, methods=['GET'], permission_classes=[])
    def ads(self, request, pk=None):

        return JsonResponse({
            'ios_interstitial': "ca-app-pub-9369132738006643/7186179931",
            'ios_banner': "ca-app-pub-9369132738006643/3869438496",
            'android_interstitial': "",
            'android_banner': "",
        })

    @action(detail=False, methods=['GET'], permission_classes=[])
    def user_daily(self, request, pk=None):
        user_id = request.user.id
        # Date given            2023-10-09
        # Date stored in DB as  2023-10-09 00:00:00+00
        # Start                 2023-10-09 00:00:00-07
        # End                   2023-10-09 23:59:59-07

        data = dict()
        today = today_UTC(request)

        start = datetime.combine(today, time.min).strftime("%Y-%m-%d %H:%M:%S%z")
        end = datetime.combine(today, time.max).strftime("%Y-%m-%d %H:%M:%S%z")
        print("Daily snapshot date: ", today)
        print("Daily snapshot Start date: ", start)
        print("Daily snapshot End date: ", end)



        wgs = WorkoutGroups.objects.filter(
            owned_by_class=False,
            owner_id=user_id,
            archived=False,
            for_date__gte= start,
            for_date__lte= end,
        )
        # cwgs = CompletedWorkoutGroups.objects.filter(
        #     user_id=user_id,
        #     for_date__gte= start,
        #     for_date__lte= end,
        # )
        print('\n', f"Found user daily workouts ({user_id=}):", '\n',)
        for wg in wgs:
            print(wg.for_date)
        print("--END_DAILY_WORKOUT--")


        data['created_workout_groups'] = wgs
        # data['completed_workout_groups'] = cwgs

        return Response(
            list(chain(
                WorkoutGroupsSerializer(
                    wgs,
                    context={'request': request, },
                    many=True
                ).data,
                # CompletedWorkoutGroupsSerializer(
                #     cwgs,
                #     context={'request': request, },
                #     many=True
                # ).data
            ))
        )


class AppControlViewSet(viewsets.ViewSet):
    '''
     Returns workouts between a range of dates either for a user's workouts or a classes workouts.
    '''
    @action(detail=False, methods=['GET'], permission_classes=[])
    def membership_on(self, request, pk=None):

        return JsonResponse({
            'membership_on': False
        })


