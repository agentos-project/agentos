import logging

from django.test import Client, LiveServerTestCase
from django.test.utils import override_settings
from django.urls import reverse
from registry.models import Component

logger = logging.getLogger(__name__)


@override_settings(DEBUG=True)
class ViewTests(LiveServerTestCase):
    def setUp(self):
        # TODO add some data
        Component.objects.create(
            identifier="gghhjj",
            body={"data": {"tags": {"pcs.is_agent_run": True}}},
        )
        self.client = Client()

    def test_index(self):
        self.client.get(reverse("index"))

    def test_run_list(self):
        self.client.get(reverse("run-list"))

    def test_run_detail(self):
        # TODO
        self.assertEqual(0, 1)

    @override_settings(DEBUG=False)
    def test_empty_database_debug_false(self):
        self.assertEqual(Component.objects.count(), 1)
        response = self.client.get(reverse("empty-database"))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Component.objects.count(), 1)

    def test_empty_database_debug_true(self):
        self.assertEqual(Component.objects.count(), 1)
        response = self.client.get(reverse("empty-database"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Component.objects.count(), 0)
