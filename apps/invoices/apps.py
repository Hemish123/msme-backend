from django.apps import AppConfig


class InvoicesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.invoices'

    def ready(self):
        import os
        # Only start scheduler in the actual worker process (not the reloader)
        if os.environ.get('RUN_MAIN', None) == 'true':
            from .scheduler import start_scheduler
            start_scheduler()
    verbose_name = 'Invoices'
