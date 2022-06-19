import logging

from django.test import LiveServerTestCase
# from registry.models import Component
from registry.tests.utils import (
    FIXTURE_FILE,
    create_test_fixture,
    load_or_create_fixture,
)

logger = logging.getLogger(__name__)


class IntegrationTestCases(LiveServerTestCase):
    def test_run_and_publish(self):
        FIXTURE_FILE.unlink(missing_ok=True)
        self.assertEqual(Component.objects.count(), 0)
        create_test_fixture(self.live_server_url)
        self.assertEqual(Component.objects.count(), 20)

    def test_web_registry_integration(self):
        load_or_create_fixture(self.live_server_url)
        self.assertEqual(0, 1)
