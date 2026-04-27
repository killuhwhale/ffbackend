from django.core.management.base import BaseCommand
from django.utils import timezone
from gyms.models import TokenQuota

class Command(BaseCommand):
    help = 'Reset token_quota for all users where reset_at is past due.'

    def handle(self, *args, **kwargs):
        updated = TokenQuota.objects.filter(
            reset_at__lte = timezone.now(),
        ).update(remaining_tokens=0)
        self.stdout.write(f"Reset {updated} rows. {timezone.now()=}")
