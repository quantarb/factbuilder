from django.apps import AppConfig

class FactsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'facts'

    def ready(self):
        # Import signals or other startup logic if needed
        pass
