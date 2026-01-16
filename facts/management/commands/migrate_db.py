from django.core.management import call_command
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Runs database migrations'

    def handle(self, *args, **options):
        self.stdout.write("Running migrations...")
        call_command('migrate')
        self.stdout.write(self.style.SUCCESS("Migrations completed."))
