import datetime
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.utils import OperationalError

class Command(BaseCommand):
    help = 'Checks database connection health and system status'

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("=== RideBasket Backend Health Check ==="))
        self.stdout.write(f"Timestamp: {datetime.datetime.now().isoformat()}")
        
        # Test Database Connection
        try:
            connection.ensure_connection()
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
                
            db_engine = connection.settings_dict['ENGINE'].split('.')[-1]
            db_name = connection.settings_dict['NAME']
            db_host = connection.settings_dict['HOST']
            db_port = connection.settings_dict['PORT']
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"✔ Database Status : CONNECTED ({db_engine.upper()})\n"
                    f"✔ Database Host   : {db_host}:{db_port}\n"
                    f"✔ Database Name   : {db_name}"
                )
            )
        except OperationalError as e:
            self.stdout.write(
                self.style.ERROR(
                    f"✖ Database Status : FAILED TO CONNECT\n"
                    f"Error Details     : {str(e)}"
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"✖ Unexpected Error: {str(e)}")
            )