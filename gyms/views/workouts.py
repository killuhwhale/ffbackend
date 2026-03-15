import json
from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from typing import List

from gyms.models import (
    GymClasses, LikedWorkouts, WorkoutDualItems, WorkoutGroups,
    WorkoutItems, WorkoutNames, WorkoutStats, Workouts,
)
from gyms.serializers import (
    WorkoutCreateSerializer,
    WorkoutGroupsCreateSerializer,
    WorkoutGroupsSerializer,
    WorkoutSerializer,
    WorkoutGroupsAutoCompletedSerializer,
)
from .helpers import (
    WORKOUT_FILES,
    FILES_KINDS,
    delete_media,
    is_gym_class_owner,
    is_gym_owner,
    is_gymclass_coach,
    jbool,
    to_data,
    to_err,
    today_UTC,
    upload_media,
)
from .permissions import (
    EditWorkoutMediaPermission,
    SelfActionPermission,
    WorkoutGroupsPermission,
    WorkoutPermission,
)


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
            if not data['owned_by_class']:
                data['owner_id'] = request.user.id
            print("Attempting to create WorkoutGroup with data: ", data)
            workout_group, newly_created = WorkoutGroups.objects.get_or_create(
                **{**data, 'media_ids': []})
            if not newly_created:
                return Response(to_err("Workout already created. Must delete and reupload w/ media or edit workout.", ))
        except Exception as e:
            print("Error creating workout group:", e)
            return Response(to_err(f"Error creating workout group: {e}", exception=e), status=422)
        return Response(WorkoutGroupsSerializer(workout_group, context={'request': request}).data)

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
                workout_stats_json = workout_json['stats']
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

                    if workout.scheme_type <= 2:
                        new_items.append(WorkoutItems(
                            **{**item_json, "workout": Workouts(id=workout.id), "name": WorkoutNames(id=item_json['name']['id'])}))
                    else:
                        new_items.append(WorkoutDualItems(
                            **{**item_json, "workout": Workouts(id=workout.id), "name": WorkoutNames(id=item_json['name']['id'])}))

                if workout.scheme_type <= 2:
                    WorkoutItems.objects.bulk_create(new_items)
                else:
                    WorkoutDualItems.objects.bulk_create(new_items)

        return Response(WorkoutGroupsSerializer(workout_group, context={'request': request}).data)

    def last_id_from_media(self, cur_media_ids: List[str]) -> int:
        last_id = 0
        if not cur_media_ids:
            return last_id

        media_ids = sorted(cur_media_ids, key=lambda p: p.split(".")[0])
        last_media_id = media_ids[-1]
        return int(last_media_id.split(".")[0])

    @action(detail=True, methods=['post'], permission_classes=[EditWorkoutMediaPermission])
    def add_media_to_workout(self, request, pk=None):
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

    @action(detail=True, methods=['get'], permission_classes=[])
    def user_workouts(self, request, pk=None):
        try:
            owner_id = request.user.id
            print("Owner id", owner_id)
            workout_groups: WorkoutGroups = WorkoutGroups.objects.get(
                owner_id=owner_id, owned_by_class=False, id=pk)
            return Response(WorkoutGroupsSerializer(workout_groups, context={'request': request, }).data)
        except Exception as e:
            print("\n\n\n\n\nWorkoutGroupsViewSet user_workouts", e)
            print("Request", request)
            return Response({'error': "Failed get user's workout group."}, status=500)

    @action(detail=False, methods=['get'], permission_classes=[SelfActionPermission])
    def last_x_workout_groups(self, request, pk=None):
        owner_id = request.user.id
        workout_groups = (
            WorkoutGroups.objects
            .filter(owner_id=owner_id, owned_by_class=False, for_date__lt=today_UTC(request))
            .order_by('-for_date')[:10]
        )
        return Response(WorkoutGroupsSerializer(workout_groups, many=True, context={'request': request, }).data)

    @action(detail=True, methods=['get'], permission_classes=[])
    def class_workouts(self, request, pk=None):
        ''' Returns all workouts for a gymclass. '''
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

    @action(detail=False, methods=['post'], permission_classes=[SelfActionPermission])
    def favorite(self, request, pk=None):
        try:
            user_id = request.data.get("user_id")
            workout_id = request.data.get("workout")
            LikedWorkouts.objects.create(
                user_id=user_id, workout=workout_id)
            return Response(to_data("Favorited!"))
        except Exception as e:
            return Response(to_err("Failed to favorite"))

    @action(detail=False, methods=['DELETE'], permission_classes=[SelfActionPermission])
    def unfavorite(self, request, pk=None):
        try:
            user_id = request.data.get("user_id")
            workout_id = request.data.get("workout")
            LikedWorkouts.objects.get(
                user_id=user_id, workout=workout_id).delete()
            return Response(to_data("Unfavorited!"))
        except Exception as e:
            return Response(to_err("Failed to unfavorite"))

    @action(detail=False, methods=['POST'], permission_classes=[SelfActionPermission])
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

    @action(detail=False, methods=['POST'], permission_classes=[SelfActionPermission])
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

    @action(detail=False, methods=['POST'], permission_classes=[SelfActionPermission])
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

    @action(detail=False, methods=['POST'], permission_classes=[])
    def finish(self, request, pk=None):
        try:
            user_id = request.user.id
            workout_group_id = request.data.get("group")
            print(f"Finishing workout group: {workout_group_id=}")
            workout_group = WorkoutGroups.objects.get(id=workout_group_id)
            if not workout_group.workouts_set.exists():
                return Response(to_data(f"Cannot finish workoutgroup without workouts {workout_group_id=}."))
            else:
                has_items = False
                for workout in workout_group.workouts_set.all():
                    if workout.workoutitems_set.exists() or workout.workoutdualitems_set.exists():
                        has_items = True
                if not has_items:
                    return Response(to_data("Cannot finish workoutgroup without workout items."))

            if workout_group.owned_by_class:
                gym_class = GymClasses.objects.get(id=workout_group.owner_id)
                if (not is_gym_class_owner(request.user, gym_class) and
                        not is_gymclass_coach(request.user, gym_class)):
                    return Response({"error": "User is not owner or coach"})
            elif not str(user_id) == str(workout_group.owner_id):
                print("User is not owner")
                return Response({"error": "User is not owner"})

            workout_group.finished = True
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
            workout_group.date_archived = timezone.now()
            workout_group.save()
            return Response(WorkoutGroupsSerializer(workout_group, context={'request': request}).data)
        workout_group.delete()
        return Response(to_data('Deleted WorkoutGroup'))

    def get_queryset(self):
        '''Affects destroy!'''
        if self.request.method == "DELETE":
            return super().get_queryset()

        queryset = super().get_queryset().order_by('for_date')
        queryset = queryset[:40]
        return queryset


class WorkoutsViewSet(viewsets.ModelViewSet, WorkoutPermission):
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

            return Response(WorkoutCreateSerializer(workout).data)
        except Exception as err:
            print(f"Error creating Workout: ", err)
            return Response(to_err(str(err), err))

    def update(self, request, *args, **kwargs):
        print(f"PUT Update: {args=} {kwargs=}")
        try:
            partial = kwargs.pop('partial', False)
            workout = self.get_object()

            serializer = self.get_serializer(workout, data=request.data, partial=partial)

            print(f"update: {request.data=}")

            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as err:
            print(f"Update Workout error: {err=}")
        return Response({'detail': "Update Workout error"})

    def destroy(self, request, pk=None):
        workout_id = pk
        workout = Workouts.objects.get(id=workout_id)
        print(f"Destroying wod from group {workout.group.finished=}")
        if workout.group.finished:
            return Response(to_err("Cannot remove workouts from finished workout group."), status=403)

        workout.delete()
        return Response(WorkoutSerializer(workout).data)
