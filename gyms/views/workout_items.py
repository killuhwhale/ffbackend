import json
from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from gyms.models import (
    WorkoutCategories, WorkoutDualItems, WorkoutItems,
    WorkoutNames, WorkoutStats, Workouts,
)
from gyms.serializers import (
    WorkoutCategorySerializer,
    WorkoutDualItemCreateSerializer,
    WorkoutDualItemSerializer,
    WorkoutItemCreateSerializer,
    WorkoutItemSerializer,
    WorkoutNamesSerializer,
)
from .helpers import (
    FILES_KINDS,
    NAME_FILES,
    delete_media,
    to_data,
    to_err,
    upload_media,
)
from .permissions import (
    SuperUserWritePermission,
    WorkoutDualItemsPermission,
    WorkoutItemsPermission,
)


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


class WorkoutItemsViewSet(viewsets.ModelViewSet, WorkoutItemsPermission):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = WorkoutItems.objects.all()
    permission_classes = [WorkoutItemsPermission]

    def create(self, request, *args, **kwargs):
        return Response(to_err("Failed, route not available.", Exception()), status=404)

    @action(detail=False, methods=['post'], permission_classes=[WorkoutItemsPermission])
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
                return Response(to_data("Workout not found"))

            print('Items', workout_items)
            print('Workout ID:', workout_id)

            items = []
            for w in workout_items:
                try:
                    del w['id']
                    del w['workout']
                except Exception as err:
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

    @action(detail=False, methods=['post'], permission_classes=[WorkoutItemsPermission])
    def items(self, request, pk=None):
        return self.create_items(request)

    def get_serializer_class(self):
        if self.action == 'list' or self.action == 'retrieve':
            return WorkoutItemSerializer
        if self.action == 'create':
            return WorkoutItemCreateSerializer
        return WorkoutItemSerializer


class WorkoutDualItemsViewSet(viewsets.ModelViewSet, WorkoutItemsPermission):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = WorkoutDualItems.objects.all()
    permission_classes = [WorkoutDualItemsPermission]

    def create(self, request, *args, **kwargs):
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

    @action(detail=False, methods=['post'], permission_classes=[WorkoutDualItemsPermission])
    def record_items(self, request, pk=None):
        '''Updates items once the workout is completed.'''
        try:
            print("Updating workout Dual Items: ", request.data)
            workout_items = json.loads(request.data.get("items", '[]'))
            workout_id = request.data.get("workout", 0)
            workout = Workouts.objects.get(id=workout_id)

            if not workout:
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

    def get_serializer_class(self):
        if self.action == 'list' or self.action == 'retrieve':
            return WorkoutDualItemSerializer
        if self.action == 'create':
            return WorkoutDualItemCreateSerializer
        return WorkoutDualItemSerializer


class WorkoutNamesViewSet(viewsets.ModelViewSet, SuperUserWritePermission):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = WorkoutNames.objects.all()
    serializer_class = WorkoutNamesSerializer
    permission_classes = [SuperUserWritePermission]

    def create(self, request):
        data = request.data.copy().dict()
        files = request.data.getlist("files", [])
        categories = json.loads(data['categories'])
        primary = data['primary']
        secondary = data['secondary']
        del data['files']
        del data['categories']
        del data['primary']
        del data['secondary']

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

    @action(detail=True, methods=['post'], permission_classes=[])
    def add_media_to_workout_name(self, request, pk=None):
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
    permission_classes = [SuperUserWritePermission]
