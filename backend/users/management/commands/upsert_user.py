from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from users.models import UserRole


User = get_user_model()


class Command(BaseCommand):
    help = "Create or update a user with a specific platform role."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)
        parser.add_argument("--password", required=True)
        parser.add_argument("--role", choices=UserRole.values, required=True)
        parser.add_argument("--email", default="")
        parser.add_argument("--region", default="")
        parser.add_argument("--staff", action="store_true")
        parser.add_argument("--superuser", action="store_true")

    def handle(self, *args, **options):
        username = options["username"].strip()
        password = options["password"]
        role = options["role"]

        if not username:
            raise CommandError("username must not be empty")

        user, created = User.objects.get_or_create(username=username)
        user.email = options["email"].strip()
        user.region = options["region"].strip()
        user.role = role
        user.is_active = True
        user.is_staff = options["staff"] or role == UserRole.ADMIN
        user.is_superuser = options["superuser"] or role == UserRole.ADMIN
        user.set_password(password)
        user.save()

        action = "created" if created else "updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"{action}: username={user.username} role={user.role} "
                f"is_staff={user.is_staff} is_superuser={user.is_superuser}"
            )
        )
