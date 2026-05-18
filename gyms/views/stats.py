from datetime import datetime, time
from itertools import chain
import copy
import logging
from django.http import JsonResponse
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from gyms.models import CompletedWorkoutGroups, WorkoutGroups
from gyms.serializers import (
    CompletedWorkoutGroupsSerializer,
    WorkoutGroupsSerializer,
)
from .ai_helpers import WORKOUT_GENERATION_RULES, base_schema
from .helpers import today_UTC, tz

logger = logging.getLogger(__name__)


def _strip_ai_schema_metadata(value):
    if isinstance(value, dict):
        value.pop("default", None)
        for nested in value.values():
            _strip_ai_schema_metadata(nested)
    elif isinstance(value, list):
        for nested in value:
            _strip_ai_schema_metadata(nested)
    return value


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

        logger.debug("User workouts stats user_id=%s start=%s end=%s query_params=%s", user_id, start, end, request.query_params)
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

        logger.debug("User workouts stats created_count=%d completed_count=%d", wgs.count(), cwgs.count())

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
        logger.debug("Daily snapshot user_id=%s today=%s start=%s end=%s", user_id, today, start, end)

        wgs = WorkoutGroups.objects.filter(
            owned_by_class=False,
            owner_id=user_id,
            archived=False,
            for_date__gte=start,
            for_date__lte=end,
        )

        logger.debug("Found user daily workouts user_id=%s count=%d", user_id, wgs.count())

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

    @action(detail=False, methods=['GET'], permission_classes=[])
    def ai_provider_config(self, request, pk=None):
        workout_schema = copy.deepcopy(base_schema["parameters"])
        workout_schema["additionalProperties"] = False
        workout_schema["required"] = [
            "goal",
            "title",
            "description",
            "workout_type",
            "scheme_rounds",
            "items",
        ]

        item_schema = workout_schema["properties"]["items"]["items"]
        item_schema["additionalProperties"] = False
        item_properties = item_schema.get("properties", {})
        if "name" in item_properties:
            item_properties["name"] = {
                "type": "string",
                "description": "Exact workout name from the allowed workout names list.",
            }
        item_schema["required"] = list(item_properties.keys())
        workout_schema = _strip_ai_schema_metadata(workout_schema)

        return JsonResponse({
            "version": 1,
            "cache_ttl_seconds": 86400,
            "providers": {
                "openai": {
                    "chat_url": "https://api.openai.com/v1/responses",
                    "workout_url": "https://api.openai.com/v1/responses",
                    "chat_model": "gpt-5-mini",
                    "workout_model": "gpt-5-mini",
                },
                "anthropic": {
                    "chat_url": "https://api.anthropic.com/v1/messages",
                    "workout_url": "https://api.anthropic.com/v1/messages",
                    "chat_model": "claude-sonnet-4-20250514",
                    "workout_model": "claude-sonnet-4-20250514",
                    "anthropic_version": "2023-06-01",
                },
                "gemini": {
                    "chat_url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
                    "workout_url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
                    "chat_model": "gemini-2.5-flash",
                    "workout_model": "gemini-2.5-flash",
                },
            },
            "workout": {
                "tool_name": base_schema["name"],
                "tool_description": base_schema.get("description", "Generate workout items."),
                "response_schema": workout_schema,
                "system_rules": WORKOUT_GENERATION_RULES,
                "max_tokens": {
                    "anthropic": 4096,
                },
            },
        })
