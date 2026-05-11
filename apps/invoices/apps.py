from django.apps import AppConfig


class InvoicesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.invoices'

    def ready(self):
        import os
        import sys
        # Check if we are running locally with runserver
        is_runserver = 'runserver' in sys.argv
        
        # Only start scheduler in the actual worker process (not the reloader)
        # If not using runserver (e.g., production Azure), start it immediately.
        if not is_runserver or os.environ.get('RUN_MAIN') == 'true':
            from .scheduler import start_scheduler
            start_scheduler()
        
    verbose_name = 'Invoices'
