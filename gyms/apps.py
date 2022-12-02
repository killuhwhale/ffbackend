from django.apps import AppConfig
from django.db.models.signals import post_delete


class GymsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'gyms'

    def ready(self):
        # Implicitly connect signal handlers decorated with @receiver.
        from . import signals
        # Explicitly connect a signal handler.
