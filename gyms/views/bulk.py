import json
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate

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
        print("Request template user: ", request.user)
        factory = APIRequestFactory()
        created_groups = []
        user = request.user
        tz = request.tz

        groups = request.data.get("template", [])
        if len(groups) < 1:
            return Response([])

        template_name = groups[0]["group"]['template_name']
        template_num = next_template_num(request.user, template_name)
        for grp in groups:
            group = {**grp["group"]}

            group['template_num'] = template_num
            group['creation_source'] = 'template'

            group_req = factory.post(
                '/workoutGroups/',
                group,
                format='multipart'
            )

            group_req.tz = tz
            force_authenticate(group_req, user=user)

            # Import here to avoid circular imports
            from .workouts import WorkoutGroupsViewSet, WorkoutsViewSet
            from .workout_items import WorkoutItemsViewSet

            group_resp = WorkoutGroupsViewSet.as_view({"post": "create"})(group_req)

            print(f"{group_resp.status_code=}")

            if group_resp.status_code not in (status.HTTP_200_OK, status.HTTP_201_CREATED):
                return group_resp

            group_id = group_resp.data["id"]
            created_groups.append(group_id)

            print("Creating workouts for group: ", grp.get("workouts", []))
            for wk in grp.get("workouts", []):
                wk_payload = {**wk["workout"], "group": group_id}
                workout_req = factory.post(
                    '/workouts/',
                    wk_payload,
                    format='multipart'
                )

                force_authenticate(workout_req, user=user)
                workout_req.tz = tz

                wk_resp = WorkoutsViewSet.as_view({"post": "create"})(workout_req)
                if wk_resp.status_code not in (status.HTTP_200_OK, status.HTTP_201_CREATED):
                    return wk_resp

                workout_id = wk_resp.data["id"]

                items_payload = {
                    "items": json.dumps(wk["items"]),
                    "workout": workout_id,
                    "workout_group": group_id,
                    "tags": json.dumps(wk['tags']),
                    "names": json.dumps(wk['names']),
                }
                items_req = factory.post(
                    '/workoutItems/items/',
                    items_payload,
                    format='multipart'
                )

                force_authenticate(items_req, user=user)
                items_req.tz = tz
                items_resp = WorkoutItemsViewSet.as_view({"post": "items"})(items_req)
                if items_resp.status_code not in (status.HTTP_200_OK, status.HTTP_201_CREATED):
                    return items_resp

        return Response(
            {"created_groups": created_groups},
            status=status.HTTP_201_CREATED
        )
