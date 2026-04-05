import json
from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .helpers import cur_template_num, next_template_num, to_err
from .permissions import SelfActionPermission


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
            from gyms.models import WorkoutGroups
            user = request.user
            template_name = request.data['template_name']

            template_wg = WorkoutGroups.objects.filter(
                is_template=True,
                owner_id=user.id,
                template_name=template_name,
                finished=False,
                template_num=cur_template_num(user, template_name)
            )

            for w in template_wg:
                w.delete()
            return Response({"data": "Successfully removed un-done/finished templates"})
        except Exception as err:
            print("Failed to reset template: ", request.data, err)
        return Response({"err": "Failed to reset template"})

    @action(detail=False, methods=['POST'], permission_classes=[SelfActionPermission])
    def create_template(self, request):
        """
        Creates all template WorkoutGroups, Workouts, WorkoutItems, and
        WorkoutStats in a single request using direct ORM calls inside one
        atomic transaction.  This bypasses the per-group permission / rate-limit
        checks that block free-tier users after the first WorkoutGroup.
        """
        from gyms.models import (
            WorkoutGroups, Workouts, WorkoutItems, WorkoutNames, WorkoutStats,
        )
        from gyms.serializers import WorkoutGroupsCreateSerializer

        user = request.user
        groups = request.data.get("template", [])
        if len(groups) < 1:
            return Response([])

        template_name = groups[0]["group"]["template_name"]
        template_num = next_template_num(user, template_name)
        created_groups = []

        try:
            with transaction.atomic():
                for grp in groups:
                    group_data = {**grp["group"]}
                    group_data["owner_id"] = str(user.id)
                    group_data["owned_by_class"] = False
                    group_data["template_num"] = template_num
                    group_data["creation_source"] = "template"
                    group_data["media_ids"] = "[]"

                    serializer = WorkoutGroupsCreateSerializer(data=group_data)
                    serializer.is_valid(raise_exception=True)

                    workout_group, newly_created = WorkoutGroups.objects.get_or_create(
                        **serializer.validated_data
                    )
                    if not newly_created:
                        continue

                    created_groups.append(workout_group.id)

                    for wk in grp.get("workouts", []):
                        wk_data = {**wk["workout"], "group_id": workout_group.id}
                        workout, _ = Workouts.objects.get_or_create(**wk_data)

                        # Create WorkoutItems in bulk
                        items_raw = wk.get("items", [])
                        item_objs = []
                        for item in items_raw:
                            item_copy = {**item}
                            # Remove fields that are set via FK objects
                            item_copy.pop("id", None)
                            item_copy.pop("workout", None)
                            item_copy.pop("date", None)
                            name_val = item_copy.pop("name")
                            name_id = name_val["id"] if isinstance(name_val, dict) else name_val
                            item_objs.append(WorkoutItems(
                                **item_copy,
                                workout=workout,
                                name=WorkoutNames(id=name_id),
                            ))
                        if item_objs:
                            WorkoutItems.objects.bulk_create(item_objs)

                        # Create WorkoutStats
                        tags = wk.get("tags", {})
                        names = wk.get("names", {})
                        WorkoutStats.objects.get_or_create(
                            workout=workout,
                            defaults={"tags": tags, "items": names},
                        )

        except Exception as e:
            print("Error in bulk create_template: ", e)
            return Response(
                to_err(f"Failed to create template: {e}", exception=e),
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        return Response(
            {"created_groups": created_groups},
            status=status.HTTP_201_CREATED,
        )
