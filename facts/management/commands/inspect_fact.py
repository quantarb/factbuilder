from django.core.management.base import BaseCommand
from facts.models import FactDefinitionVersion

class Command(BaseCommand):
    help = 'Inspects a fact version'

    def add_arguments(self, parser):
        parser.add_argument('fact_id', type=str)

    def handle(self, *args, **options):
        fact_id = options['fact_id']
        version = FactDefinitionVersion.objects.filter(fact_definition_id=fact_id, status='approved').last()
        if version:
            self.stdout.write(f"Fact: {fact_id} v{version.version}")
            self.stdout.write(f"Requires: {version.requires}")
            self.stdout.write("Code:")
            self.stdout.write(version.code)
        else:
            self.stdout.write(f"No approved version for {fact_id}")
