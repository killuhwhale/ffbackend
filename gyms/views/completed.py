import json
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from typing import List

from gyms.models import (
    CompletedWorkoutDualItems, CompletedWorkoutGroups, CompletedWorkoutItems,
    CompletedWorkouts, WorkoutGroups, WorkoutNames, Workouts,
)
from gyms.serializers import (
    CompletedWorkoutCreateSerializer,
    CompletedWorkoutGroupsSerializer,
    CompletedWorkoutSerializer,
)
from .helpers import (
    COMP_WORKOUT_FILES,
    FILES_KINDS,
    DestroyWithPayloadMixin,
    delete_media,
    to_data,
    to_err,
    upload_media,
)
from .permissions import (
    CompletedWorkoutGroupsPermission,
    CompletedWorkoutsPermission,
    EditWorkoutMediaPermission,
)


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

                if _w["scheme_type"] <= 2:
                    print("Attempt create items")
                    allItems.extend(self.create_items(request, workout_items, completed_workout.id))
                else:
                    print("Attempt create dual items")
                    allDualItems.extend(self.record_dualitems(request, workout_items, completed_workout.id))

            CompletedWorkoutItems.objects.bulk_create(allItems)
            CompletedWorkoutDualItems.objects.bulk_create(allDualItems)

        except Exception as e:
            comp_workout_group.delete()
            msg = f"Error creating CompleteWorkoutItems {e}"
            print(msg, e)
            return Response(to_err(msg))

        return Response(CompletedWorkoutGroupsSerializer(comp_workout_group).data)

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

    @action(detail=True, methods=['delete'], permission_classes=[EditWorkoutMediaPermission])
    def remove_media_from_workout(self, request, pk=None):
        try:
            workout_group_id = pk
            remove_media_ids = json.loads(request.data.get("media_ids"))
            workout_group = CompletedWorkoutGroups.objects.get(id=workout_group_id)
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
            return Response(CompletedWorkoutGroupsSerializer(workout_groups).data)
        except Exception as e:
            print(e)
            return Response(to_err("Failed get user's workouts."))

    @action(detail=True, methods=['get'], permission_classes=[])
    def completed_workout_group(self, request, pk=None):
        try:
            workout_groups: CompletedWorkoutGroups = CompletedWorkoutGroups.objects.get(id=pk)
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
        return Response(to_err("Failed, route not available.", Exception()), status=404)

    def partial_update(self, request, *args, **kwargs):
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
        return Response(to_err("Failed, route not available.", Exception()), status=404)

    def update(self, request, *args, **kwargs):
        return Response(to_err("Failed, route not available.", Exception()), status=404)

    def partial_update(self, request, *args, **kwargs):
        return Response(to_err("Failed, route not available.", Exception()), status=404)

    def destroy(self, request, *args, **kwargs):
        return Response(to_err("Failed, route not available.", Exception()), status=404)
