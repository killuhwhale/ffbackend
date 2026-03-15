from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from typing import List

from django.contrib.auth import get_user_model

from gyms.models import ClassMembers, Coaches
from gyms.serializers import (
    ClassMembersCreateSerializer,
    ClassMembersSerializer,
    CoachesCreateSerializer,
    CoachesSerializer,
    UserWithoutEmailSerializer,
)
from .helpers import to_data, to_err
from .permissions import CoachPermission, MemberPermission

User = get_user_model()


class CoachesViewSet(viewsets.ModelViewSet, CoachPermission):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = Coaches.objects.all()
    permission_classes = [CoachPermission]

    @action(detail=True, methods=['GET'])
    def coaches(self, request, pk=None):
        '''Gets all coaches for a class. '''
        coaches: List[Coaches] = Coaches.objects.filter(gym_class__id=pk)
        ids = [c.user_id for c in coaches]
        print("Coach ids: ", ids)

        users = User.objects.filter(id__in=ids)
        return Response(UserWithoutEmailSerializer(users, many=True).data)

    @action(detail=False, methods=['DELETE'])
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
        return Response(to_err("Failed, route not available.", Exception()), status=404)

    def partial_update(self, request, *args, **kwargs):
        return Response(to_err("Failed, route not available.", Exception()), status=404)

    def destroy(self, request, *args, **kwargs):
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

    @action(detail=True, methods=['GET'])
    def members(self, request, pk=None):
        '''Gets all members for a class. '''
        members: List[ClassMembers] = ClassMembers.objects.filter(gym_class__id=pk)
        ids = [c.user_id for c in members]
        print("Coach ids: ", ids)

        users = User.objects.filter(id__in=ids)
        return Response(UserWithoutEmailSerializer(users, many=True).data)

    @action(detail=False, methods=['DELETE'])
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
        return Response(to_err("Failed, route not available.", Exception()), status=404)

    def partial_update(self, request, *args, **kwargs):
        return Response(to_err("Failed, route not available.", Exception()), status=404)

    def destroy(self, request, *args, **kwargs):
        return Response(to_err("Failed, route not available.", Exception()), status=404)

    def get_serializer_class(self):
        if self.action == 'list' or self.action == 'retrieve':
            return ClassMembersSerializer
        if self.action == 'create':
            return ClassMembersCreateSerializer
        return ClassMembersSerializer
