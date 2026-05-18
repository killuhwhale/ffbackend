import logging
from rest_framework.permissions import BasePermission, SAFE_METHODS
from rest_framework.response import Response

from gyms.models import (
    ClassMembers, CompletedWorkoutGroups, CompletedWorkouts,
    GymClasses, WorkoutGroups, Workouts,
)
from .helpers import (
    check_users_workouts_and_completed_today,
    is_gym_class_owner,
    is_gym_owner,
    is_gymclass_coach,
    is_gymclass_member,
    is_member,
    jbool,
    to_err,
)

logger = logging.getLogger(__name__)


class GymPermission(BasePermission):
    message = "Only Gym owners can remove their gym"

    def has_permission(self, request, view):
        if view.action == "update" or view.action == "partial_update" or request.method == "PATCH":
            return False
        elif request.method in SAFE_METHODS:
            return True
        elif request.method == "POST" and view.action == "create":
            return is_member(request)
        elif request.method == "DELETE":
            gym_id = view.kwargs['pk']
            logger.debug("Deleting gym gym_id=%s is_owner=%s", gym_id, is_gym_owner(request.user, gym_id))

            from gyms.models import Gyms
            gym = Gyms.objects.get(id=gym_id)
            logger.debug("Gym delete target gym_id=%s", gym.id)
            return is_gym_owner(request.user, gym_id)
        return False


class GymClassPermission(BasePermission):
    message = "Only Gym owners can create or remove classes"

    def has_permission(self, request, view):
        if view.action == "update" or view.action == "partial_update" or request.method == "PATCH":
            return False
        elif request.method in SAFE_METHODS:
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
        logger.debug("Workout permission method=%s action=%s", request.method, view.action)
        if view.action == "partial_update" or request.method == "PATCH":
            return False
        elif request.method in SAFE_METHODS:
            return True
        elif request.method == "POST" and view.action == "create" or request.method == "PUT":
            group_id = request.data.get("group", 0)
            if not group_id:
                return Response(to_err("Error finding group id"))

            workout_group: WorkoutGroups = WorkoutGroups.objects.get(id=group_id)
            owner_id = workout_group.owner_id

            if workout_group.owned_by_class:
                gym_class = GymClasses.objects.get(id=owner_id)
                return is_gym_owner(request.user, gym_class.gym.id) or is_gymclass_coach(request.user, gym_class)
            return not workout_group.owned_by_class and str(owner_id) == str(request.user.id)
        elif request.method == "DELETE":
            workout_id = view.kwargs['pk']
            workout = Workouts.objects.get(id=workout_id)
            workout_group_id = workout.group.id
            workout_group = WorkoutGroups.objects.get(id=workout_group_id)
            owned_by_class = workout_group.owned_by_class

            logger.debug(
                "Delete workout workout_id=%s owned_by_class=%s user_id=%s owner_id=%s",
                workout_id, owned_by_class, request.user.id, workout_group.owner_id,
            )
            if owned_by_class:
                gym_class = GymClasses.objects.get(id=workout_group.owner_id)
                logger.debug(
                    "Delete class-owned workout user_id=%s gym_id=%s is_owner=%s is_coach=%s",
                    request.user.id,
                    gym_class.gym.id,
                    is_gym_owner(request.user, gym_class.gym.id),
                    is_gymclass_coach(request.user, gym_class),
                )
                return is_gym_owner(request.user, gym_class.gym.id) or is_gymclass_coach(request.user, gym_class)
            else:
                return not owned_by_class and str(request.user.id) == str(workout_group.owner_id)


class SuperUserWritePermission(BasePermission):
    message = """Only admins can create/delete workoutNames."""

    def has_permission(self, request, view):
        if view.action == "update" or view.action == "partial_update" or request.method == "PATCH":
            return False
        elif request.method in SAFE_METHODS:
            return True
        elif request.method == "POST" and view.action == "create":
            return request.user.is_superuser
        elif request.method == "DELETE":
            return request.user.is_superuser
        return False


class WorkoutGroupsPermission(BasePermission):
    message = """Only users can create/delete workouts for themselves or
                for a class they own or are a coach of."""

    def has_permission(self, request, view):
        logger.debug("WorkoutGroup permission method=%s action=%s", request.method, view.action)

        if view.action == "update" or view.action == "partial_update" or request.method == "PATCH":
            return False
        elif request.method in SAFE_METHODS:
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
                gym_class = GymClasses.objects.get(id=request.data.get("owner_id"))
                logger.debug(
                    "Checking workout group class permission permitted=%s",
                    is_gym_owner(request.user, gym_class.gym.id) or is_gymclass_coach(request.user, gym_class),
                )
                return (is_gym_owner(request.user, gym_class.gym.id) or is_gymclass_coach(request.user, gym_class)) and user_is_member

            if user_is_member:
                return not jbool(request.data.get("owned_by_class")) and \
                    str(request.user.id) == str(request.data.get("owner_id"))
            else:
                logger.debug("User not member, checking daily workout creation limit user_id=%s", request.user.id)
                return check_users_workouts_and_completed_today(request)

        elif request.method == "DELETE":
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
        if view.action == "create" or view.action == "partial_update" or view.action == "destroy":
            return False
        elif request.method in SAFE_METHODS:
            return True
        elif request.method == "POST" and (view.action == "items" or view.action == "update_items"):
            workout_id = request.data.get("workout", "0")
            logger.debug("Permission check workout items workout_id=%s", workout_id)
            if not workout_id == "0":
                workout, workout_group = None, None
                try:
                    workout = Workouts.objects.get(id=workout_id)
                    workout_group = WorkoutGroups.objects.get(id=workout.group.id)
                except Exception as e:
                    logger.debug("Workout items permission lookup failed: %s", e)
                    return False
                if not workout or not workout_group:
                    return False

                owner_id = workout_group.owner_id
                owned_by_class = workout_group.owned_by_class
                if owned_by_class:
                    gym_class = GymClasses.objects.get(id=owner_id)
                    return is_gymclass_coach(request.user, gym_class) or is_gym_class_owner(request.user, gym_class)
                else:
                    return str(request.user.id) == str(owner_id)
        return False


class WorkoutDualItemsPermission(BasePermission):
    message = """Only users can create workout Items for themselves or for a class they own or are a coach of."""

    def has_permission(self, request, view):
        if view.action == "create" or view.action == "update" or view.action == "partial_update" or view.action == "destroy":
            return False
        elif request.method in SAFE_METHODS:
            return True
        elif request.method == "POST" and (view.action == "items" or view.action == "update_items" or view.action == "record_items"):
            workout_id = request.data.get("workout", "0")
            logger.debug("Permission check workout dual items workout_id=%s", workout_id)
            if not workout_id == "0":
                workout, workout_group = None, None
                try:
                    workout = Workouts.objects.get(id=workout_id)
                    workout_group = WorkoutGroups.objects.get(id=workout.group.id)
                except Exception as e:
                    logger.debug("Workout dual items permission lookup failed: %s", e)
                    return False
                if not workout or not workout_group:
                    return False

                owner_id = workout_group.owner_id
                owned_by_class = workout_group.owned_by_class
                if owned_by_class:
                    gym_class = GymClasses.objects.get(id=owner_id)
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
            return True
        elif request.method == "POST" and view.action == "create":
            if is_member(request):
                logger.debug("Completed workout group permission allowed for member user_id=%s", request.user.id)
                return True
            else:
                logger.debug("Completed workout group permission checking non-member user_id=%s", request.user.id)
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
            return True
        elif request.method == "POST" and view.action == "create":
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

        logger.debug("User self action permission target_user_id=%s request_user_id=%s", target_user_id, request.user.id)
        return target_user_id == str(request.user.id)


class SelfActionPermission(BasePermission):
    message = """
        Only users can perform actions for themselves.
            GET => ?user_id=id
            POST => { user_id: id }
    """

    def has_permission(self, request, view):
        target_user_id = None
        logger.debug("Self action permission data_keys=%s", list(request.data.keys()))
        if request.method in SAFE_METHODS:
            target_user_id = request.query_params.get("user_id")
        else:
            target_user_id = str(request.data.get("user_id"))

        logger.debug("Self action permission target_user_id=%s request_user_id=%s", target_user_id, request.user.id)
        return target_user_id == str(request.user.id)
