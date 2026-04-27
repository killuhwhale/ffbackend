from django.db.models import Max
from django.contrib.postgres.search import TrigramWordSimilarity
from django.db.models.functions import Greatest
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from gyms.models import (
    BodyMeasurements, CompletedWorkoutGroups, GymClassFavorites,
    GymFavorites, UserWorkoutMax, UserWorkoutMaxHistory, WorkoutGroups,
    WorkoutItems, WorkoutNames,
)
from gyms.serializers import (
    BodyMeasurementsSerializer,
    CombinedWorkoutGroupsSerializerNoWorkouts,
    ProfileGymClassFavoritesSerializer,
    ProfileGymFavoritesSerializer,
    ProfileSerializer,
    UserWorkoutMaxHistorySerializer,
    UserWorkoutMaxSerializer,
    WorkoutGroupsAutoCompletedSerializer,
    WorkoutGroupsSerializer,
    WorkoutNameMaxSerializer,
)
from .helpers import (
    WorkoutGroupPagination,
    cur_template_num,
    delete_user_data,
    to_err,
)
from .permissions import SelfActionPermission, SuperUserWritePermission


class ProfileViewSet(viewsets.ViewSet):

    @action(detail=False, methods=['GET'], permission_classes=[])
    def profile(self, request, pk=None):
        print(request.user)
        user_id = request.user.id
        profile_data = dict()
        profile_data['user'] = request.user
        user_id = request.user.id
        profile_data['measurements'] = BodyMeasurements.objects.filter(user_id=user_id)
        profile_data['membership_on'] = True  # Used to control if the app should respect membership features in regards to showing ads since they are test ads.

        return Response(ProfileSerializer(profile_data, context={'request': request, }).data)

    @action(detail=False, methods=['GET'], permission_classes=[])
    def gym_favs(self, request, pk=None):
        data = dict()
        user_id = request.user.id
        data['favorite_gyms'] = GymFavorites.objects.filter(user_id=user_id)
        return Response(ProfileGymFavoritesSerializer(data, context={'request': request, }).data)

    @action(detail=False, methods=['GET'], permission_classes=[])
    def gym_class_favs(self, request, pk=None):
        data = dict()
        user_id = request.user.id
        data['favorite_gym_classes'] = GymClassFavorites.objects.filter(user_id=user_id)
        return Response(ProfileGymClassFavoritesSerializer(data, context={'request': request, }).data)

    @action(detail=False, methods=['GET'], permission_classes=[SelfActionPermission])
    def workout_group_query(self, request, pk=None):
        query = request.query_params.get("query")
        user_id = request.query_params.get("user_id")

        print(f"Userid : {user_id} WG Query: {query}")

        results = (
            WorkoutGroups.objects
            .filter(owner_id=user_id)
            .annotate(
                title_similarity=TrigramWordSimilarity(query, 'title'),
                sub_similarity=Max(TrigramWordSimilarity(query, 'workouts__title')),
            )
            .annotate(similarity=Greatest('title_similarity', 'sub_similarity'))
            .filter(similarity__gt=0.3)
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
        wgs = WorkoutGroups.objects.filter(
            owner_id=user_id,
            owned_by_class=False,
            archived=False,
            template_name=template_name,
            template_num=template_num,
        ).exclude(
            is_template=False
        ).order_by('for_date')

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

        data = {
            'created_workout_groups': wgs,
            'completed_workout_groups': cwgs
        }

        combined_data = CombinedWorkoutGroupsSerializerNoWorkouts(data, context={'request': request}).data

        paginator = WorkoutGroupPagination()
        paginated_combined_data = paginator.paginate_queryset(combined_data['created_workout_groups'] + combined_data['completed_workout_groups'], request)
        return paginator.get_paginated_response(paginated_combined_data)


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


class RemoveAccount(viewsets.ViewSet):
    '''
     Deletes a user's account
    '''
    @action(detail=False, methods=['POST'], permission_classes=[SelfActionPermission])
    def remove(self, request, pk=None):
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
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
