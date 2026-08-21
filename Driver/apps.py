import sys
from datetime import datetime
from django.apps import AppConfig
from django.db import connection

class DriverConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Driver'

    def ready(self):
        # Only run on the main server process to avoid double printing
        if 'runserver' in sys.argv:
            GREEN = '\033[92m'
            RED = '\033[91m'
            RESET = '\033[0m'
            
            try:
                connection.ensure_connection()
                # Success block: Prints entirely in green
                print(f"{GREEN}=== RideBasket Backend Health Check ==={RESET}")
                print(f"{GREEN}Timestamp: {datetime.now().isoformat()}{RESET}")
                print(f"{GREEN}✔ Database Status : CONNECTED (MYSQL){RESET}")
                print(f"{GREEN}✔ Database Host   : {connection.settings_dict['HOST']}:{connection.settings_dict['PORT']}{RESET}")
                print(f"{GREEN}✔ Database Name   : {connection.settings_dict['NAME']}{RESET}")
            except Exception as e:
                # Failure block: Prints in red
                print(f"{RED}=== RideBasket Backend Health Check ==={RESET}")
                print(f"{RED}Timestamp: {datetime.now().isoformat()}{RESET}")
                print(f"{RED}❌ Database Status : FAILED ({e}){RESET}")