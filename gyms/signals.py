import json
from django.dispatch import receiver
from .s3 import s3Client
from django.db.models.signals import post_delete
from gyms.models import Gyms, GymClasses, WorkoutGroups, WorkoutNames, CompletedWorkoutGroups
from gyms.views import delete_media
s3_client = s3Client()


@receiver(post_delete, sender=Gyms)
def delete_media_from_gym(sender, **kwargs):
    print("Post delete received!", sender, kwargs)
    try:
        instance = kwargs['instance']
        return [s3_client.remove("gyms", instance.id, 'main'),
                s3_client.remove("gyms", instance.id, 'logo')]
    except Exception as e:
        print("Error removing gym media", e)
    return False


@receiver(post_delete, sender=GymClasses)
def delete_media_from_gym_class(sender, **kwargs):
    try:
        instance = kwargs['instance']
        return [s3_client.remove("classes", instance.id, 'main'),
                s3_client.remove("classes", instance.id, 'logo')]
    except Exception as e:
        print("Error removing gym_class media", e)
    return False


# @receiver(post_delete)
# def delete_media_with_unknown_ids(sender, **kwargs):
#     file_kind = ""
#     if(sender == WorkoutGroups):
#         file_kind = "workouts"
#     elif(sender == CompletedWorkoutGroups):
#         file_kind = "completedWorkouts"
#     elif(sender == WorkoutNames):
#         file_kind = "names"

#     if not file_kind:
#         return False

#     try:
#         instance = kwargs['instance']
#         removed = delete_media(instance.id, json.loads(
#             instance.media_ids), file_kind)
#         return len(removed.keys()) > 0

#     except Exception as e:
#         print("Error removing gym_class media", e)
#     return False
