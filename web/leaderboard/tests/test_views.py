import logging

from django.test import Client, LiveServerTestCase
from django.test.utils import override_settings
from django.urls import reverse
from registry.models import Component
from registry.tests.utils import load_or_create_fixture

logger = logging.getLogger(__name__)


@override_settings(DEBUG=True)
class ViewTests(LiveServerTestCase):
    def setUp(self):
        load_or_create_fixture(self.live_server_url)
        self.client = Client()

    def test_index(self):
        self.client.get(reverse("index"))

    def test_run_list(self):
        self.client.get(reverse("run-list"))

    def test_run_detail(self):
        agent_run = Component.objects.get(body__type="AgentRun")
        self.client.get(reverse("run-detail", args=(agent_run.identifier,)))

    @override_settings(DEBUG=False)
    def test_empty_database_debug_false(self):
        self.assertEqual(Component.objects.count(), 20)
        response = self.client.get(reverse("empty-database"))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Component.objects.count(), 20)

    def test_empty_database_debug_true(self):
        self.assertEqual(Component.objects.count(), 20)
        response = self.client.get(reverse("empty-database"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Component.objects.count(), 0)
