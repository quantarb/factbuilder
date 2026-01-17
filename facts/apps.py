from django.apps import AppConfig

class FactsConfig(AppConfig):
    """
    Configuration for the facts application.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'facts'

    def ready(self) -> None:
        """
        Called when the application is ready.
        """
        # Import signals or other startup logic if needed
        pass
