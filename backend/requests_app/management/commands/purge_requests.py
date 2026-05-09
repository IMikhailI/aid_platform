from django.core.management.base import BaseCommand, CommandError

from requests_app.models import AidRequest


class Command(BaseCommand):
    help = "Delete all aid requests and cascade related moderation/fraud/history data."

    def add_arguments(self, parser):
        parser.add_argument("--yes", action="store_true", help="Confirm destructive deletion.")

    def handle(self, *args, **options):
        if not options["yes"]:
            raise CommandError("This command is destructive. Re-run with --yes to confirm.")

        total = AidRequest.objects.count()
        AidRequest.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {total} requests and related data."))
