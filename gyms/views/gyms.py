from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from gyms.models import GymClasses, GymClassFavorites, GymFavorites, Gyms, WorkoutGroups
from gyms.serializers import (
    GymClassCreateSerializer,
    GymClassFavoritesSerializer,
    GymClassSerializer,
    GymClassSerializerWithWorkoutsCompleted,
    GymFavoritesSerializer,
    GymSerializer,
    GymSerializerWithoutClasses,
)
from .helpers import (
    CLASS_FILES,
    FILES_KINDS,
    GYM_FILES,
    DestroyWithPayloadMixin,
    is_gym_owner,
    is_gymclass_coach,
    is_gymclass_member,
    jbool,
    s3_client,
    to_data,
    to_err,
)
from .permissions import GymClassPermission, GymPermission


class GymViewSet(DestroyWithPayloadMixin, viewsets.ModelViewSet, GymPermission):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = Gyms.objects.all()
    serializer_class = GymSerializer
    permission_classes = [GymPermission]

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
        try:
            gym = self.queryset.get(id=pk)
            return Response(GymSerializer(gym).data)
        except Exception as e:
            print(e)
        return Response({})

    @action(detail=True, methods=['PATCH'], permission_classes=[])
    def edit_media(self, request, pk=None):
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

        queryset = super().get_queryset().order_by('title')
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

        workout_groups = []

        user_is_member = is_gymclass_member(request.user, gym_class)
        user_is_coach = is_gymclass_coach(request.user, gym_class)
        user_is_owner = is_gym_owner(request.user, gym_class.gym.id)
        is_private = gym_class.private

        workout_groups = None
        if user_is_owner or user_is_coach:
            workout_groups = WorkoutGroups.objects.filter(
                owner_id=pk,
                owned_by_class=True,
                archived=False
            ).order_by('-for_date')
        elif is_private and user_is_member or not is_private:
            workout_groups = WorkoutGroups.objects.filter(
                owner_id=pk,
                owned_by_class=True,
                finished=True,
                archived=False,
            ).order_by('-for_date')

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

        queryset = super().get_queryset().order_by('date')
        queryset = queryset[:40]
        return queryset
