import logging

from django.test import LiveServerTestCase
from registry.models import Component
from registry.tests.utils import create_test_fixture

logger = logging.getLogger(__name__)


class FixtureTests(LiveServerTestCase):
    def test_fixture(self):
        self.assertEqual(Component.objects.count(), 0)
        create_test_fixture(self.live_server_url)
        self.assertEqual(Component.objects.count(), 20)
