import os
import sys
import warnings
from django.apps import AppConfig


class RidesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'rides'

    def ready(self):
        # Only run on the main runserver process
        if 'runserver' in sys.argv and os.environ.get('RUN_MAIN') == 'true':
            from django.core.management import call_command
            
            # Suppress the "Accessing the database during app initialization" warning cleanly
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                try:
                    call_command('check_health')
                except Exception as e:
                    print(f"Health check execution failed on startup: {e}")