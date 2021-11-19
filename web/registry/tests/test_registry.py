from pathlib import Path
from django.test import TestCase
from django.test import Client
from django.urls import reverse
from registry.models import Component
from registry.models import ComponentDependency
from registry.models import Repo


class RegistryTestCases(TestCase):
    def setUp(self):
        self.client = Client()

    def test_spec_ingest(self):
        self.assertEqual(Component.objects.count(), 0)
        self.assertEqual(ComponentDependency.objects.count(), 0)
        self.assertEqual(Repo.objects.count(), 0)
        url = reverse("component-ingest-spec")
        yaml_file = open(Path(__file__).parent / "static" / "components.yaml")
        response = self.client.post(url, {"components.yaml": yaml_file})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Component.objects.count(), 7)
        self.assertEqual(ComponentDependency.objects.count(), 16)
        self.assertEqual(Repo.objects.count(), 1)
