from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

USER_NAME = "admin"
USER_EMAIL = "admin@example.com"
USER_PW = "12345678"
HELP_TEXT = f"Creates superuser '{USER_NAME}' ({USER_EMAIL}) with pw {USER_PW}"
DONE_TEXT = f"Created superuser '{USER_NAME}' ({USER_EMAIL}) with pw {USER_PW}"


class Command(BaseCommand):
    help = HELP_TEXT

    def handle(self, *args, **options):
        assert settings.DEBUG
        User.objects.create_superuser(
            username=USER_NAME, password=USER_PW, email=USER_EMAIL
        )
        print()
        print(DONE_TEXT)
        print()
