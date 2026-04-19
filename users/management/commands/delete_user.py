from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from rest_framework.authtoken.models import Token

from gyms.models import ResetPasswords, WorkoutGroups
from users.models import ConfirmationEmailCodes


User = get_user_model()


class Command(BaseCommand):
    help = (
        "Testing utility: delete a user and all associated data "
        "(workout groups they own, auth tokens, reset-password + confirmation "
        "codes, then the user row). Not intended for production use."
    )

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--email", type=str, help="Email of user to delete")
        group.add_argument("--user-id", type=int, help="ID of user to delete")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without deleting anything",
        )
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Skip interactive confirmation",
        )

    def handle(self, *args, **options):
        email = options.get("email")
        user_id = options.get("user_id")
        dry_run = options["dry_run"]

        try:
            user = User.objects.get(email=email) if email else User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise CommandError(f"No user found for email={email!r} user_id={user_id!r}")

        wg_qs = WorkoutGroups.objects.filter(
            Q(owner_id=user.id, owned_by_class=False)
        )
        token_qs = Token.objects.filter(user_id=user.id)
        reset_qs = ResetPasswords.objects.filter(email=user.email)
        confirm_qs = ConfirmationEmailCodes.objects.filter(email=user.email)

        self.stdout.write(f"User: id={user.id} email={user.email}")
        self.stdout.write(f"  WorkoutGroups (owned, not class): {wg_qs.count()}")
        self.stdout.write(f"  Auth tokens:                      {token_qs.count()}")
        self.stdout.write(f"  ResetPasswords rows:              {reset_qs.count()}")
        self.stdout.write(f"  ConfirmationEmailCodes rows:      {confirm_qs.count()}")

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run — no changes made."))
            return

        if not options["yes"]:
            answer = input(f"Delete user {user.email} and the above data? [y/N]: ")
            if answer.strip().lower() not in ("y", "yes"):
                self.stdout.write("Aborted.")
                return

        with transaction.atomic():
            wg_deleted, _ = wg_qs.delete()
            token_deleted, _ = token_qs.delete()
            reset_deleted, _ = reset_qs.delete()
            confirm_deleted, _ = confirm_qs.delete()
            user.delete()

        self.stdout.write(self.style.SUCCESS(
            f"Deleted user {user.email} "
            f"(workout_groups={wg_deleted}, tokens={token_deleted}, "
            f"reset={reset_deleted}, confirm={confirm_deleted})."
        ))
