from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Creates the MySQL database (utf8mb4) named in .env if it does not exist yet."

    def handle(self, *args, **opts):
        db = settings.DATABASES["default"]
        if "sqlite" in db["ENGINE"]:
            self.stdout.write("SQLite is in use — nothing to create.")
            return
        import pymysql

        try:
            conn = pymysql.connect(host=db["HOST"], port=int(db["PORT"]), user=db["USER"], password=db["PASSWORD"])
        except Exception as e:  # noqa: BLE001
            raise CommandError(f"Could not connect to MySQL: {e}\nCheck that MySQL is running and DB_USER / DB_PASSWORD in .env are right.")
        with conn.cursor() as cur:
            cur.execute(f"CREATE DATABASE IF NOT EXISTS `{db['NAME']}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        conn.close()
        self.stdout.write(self.style.SUCCESS(f"Database '{db['NAME']}' is ready."))
