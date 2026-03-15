from datetime import datetime, time
from itertools import chain
from django.http import JsonResponse
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from gyms.models import CompletedWorkoutGroups, WorkoutGroups
from gyms.serializers import (
    CompletedWorkoutGroupsSerializer,
    WorkoutGroupsSerializer,
)
from .helpers import today_UTC, tz


class StatsViewSet(viewsets.ViewSet):
    '''
     Returns workouts between a range of dates either for a user's workouts or a classes workouts.
    '''
    @action(detail=True, methods=['GET'], permission_classes=[])
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
            for_date__gte=start,
            for_date__lte=end,
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
            for_date__gte=start,
            for_date__lte=end,
        )

        print('\n', f"Found user daily workouts ({user_id=}):", '\n',)
        for wg in wgs:
            print(wg.for_date)
        print("--END_DAILY_WORKOUT--")

        data['created_workout_groups'] = wgs

        return Response(
            list(chain(
                WorkoutGroupsSerializer(
                    wgs,
                    context={'request': request, },
                    many=True
                ).data,
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
