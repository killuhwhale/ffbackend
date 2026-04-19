from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from rest_framework.authtoken.models import Token

from gyms.models import ResetPasswords, TokenQuota, WorkoutGroups
from users.models import ConfirmationEmailCodes


User = get_user_model()


class Command(BaseCommand):
    help = (
        "Testing utility: delete a user (or all users) and associated data "
        "(owned workout groups, auth tokens, reset-password + confirmation "
        "codes, then the user row). Not intended for production use."
    )

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--email", type=str, help="Email of user to delete")
        group.add_argument("--user-id", type=int, help="ID of user to delete")
        group.add_argument(
            "--all",
            action="store_true",
            help="Delete ALL users (excludes superusers/staff unless --include-staff).",
        )
        parser.add_argument(
            "--include-staff",
            action="store_true",
            help="With --all, also delete staff/superuser accounts.",
        )
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
        if options["all"]:
            users_qs = User.objects.all()
            if not options["include_staff"]:
                users_qs = users_qs.filter(is_staff=False, is_superuser=False)
            users = list(users_qs)
        else:
            email = options.get("email")
            user_id = options.get("user_id")
            try:
                user = User.objects.get(email=email) if email else User.objects.get(id=user_id)
            except User.DoesNotExist:
                raise CommandError(f"No user found for email={email!r} user_id={user_id!r}")
            users = [user]

        if not users:
            self.stdout.write(self.style.WARNING("No matching users."))
            return

        dry_run = options["dry_run"]
        total = {"users": 0, "wg": 0, "tokens": 0, "reset": 0, "confirm": 0, "quota": 0}

        self.stdout.write(f"Found {len(users)} user(s) to delete:")
        for user in users:
            wg_c = WorkoutGroups.objects.filter(Q(owner_id=user.id, owned_by_class=False)).count()
            tok_c = Token.objects.filter(user_id=user.id).count()
            rst_c = ResetPasswords.objects.filter(email=user.email).count()
            cnf_c = ConfirmationEmailCodes.objects.filter(email=user.email).count()
            quota_c = TokenQuota.objects.filter(user_id=str(user.id)).count()
            self.stdout.write(
                f"  id={user.id} email={user.email} "
                f"(wg={wg_c}, tokens={tok_c}, reset={rst_c}, confirm={cnf_c}, quota={quota_c})"
            )

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run — no changes made."))
            return

        if not options["yes"]:
            prompt = (
                f"Delete ALL {len(users)} users and associated data? "
                if options["all"]
                else f"Delete user {users[0].email}? "
            )
            answer = input(prompt + "[y/N]: ")
            if answer.strip().lower() not in ("y", "yes"):
                self.stdout.write("Aborted.")
                return

        with transaction.atomic():
            for user in users:
                wg_qs = WorkoutGroups.objects.filter(Q(owner_id=user.id, owned_by_class=False))
                token_qs = Token.objects.filter(user_id=user.id)
                reset_qs = ResetPasswords.objects.filter(email=user.email)
                confirm_qs = ConfirmationEmailCodes.objects.filter(email=user.email)
                quota_qs = TokenQuota.objects.filter(user_id=str(user.id))

                wg_d, _ = wg_qs.delete()
                tok_d, _ = token_qs.delete()
                rst_d, _ = reset_qs.delete()
                cnf_d, _ = confirm_qs.delete()
                quota_d, _ = quota_qs.delete()
                user.delete()

                total["users"] += 1
                total["wg"] += wg_d
                total["tokens"] += tok_d
                total["reset"] += rst_d
                total["confirm"] += cnf_d
                total["quota"] += quota_d

        self.stdout.write(self.style.SUCCESS(
            f"Deleted {total['users']} user(s) "
            f"(workout_groups={total['wg']}, tokens={total['tokens']}, "
            f"reset={total['reset']}, confirm={total['confirm']}, "
            f"quota={total['quota']})."
        ))
