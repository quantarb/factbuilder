from django.core.management import call_command
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Runs makemigrations'

    def handle(self, *args, **options):
        self.stdout.write("Running makemigrations...")
        call_command('makemigrations')
        self.stdout.write(self.style.SUCCESS("Makemigrations completed."))
