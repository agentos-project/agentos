from pathlib import Path

from django.core.files.base import File
from django.test import Client, LiveServerTestCase
from django.urls import reverse
from registry.models import Component
from registry.tests.utils import load_or_create_fixture


class RegistryTestCases(LiveServerTestCase):
    def setUp(self):
        self.client = Client()
        load_or_create_fixture(self.live_server_url)
        self.static_dir = Path(__file__).parent / "static"

    def test_run_upload_artifact(self):
        component = Component.objects.all()[0]
        self.assertFalse(bool(component.artifact_tarball))
        url = reverse(
            "component-upload-artifact", kwargs={"pk": component.identifier}
        )
        test_tarball = self.static_dir / "test_artifact_tarball.tar.gz"
        tarball = open(test_tarball, "rb")
        response = self.client.post(url, {"tarball": tarball})
        self.assertEqual(response.status_code, 200)
        component.refresh_from_db()
        self.assertTrue(bool(component.artifact_tarball))

    def test_run_download_artifact(self):
        component = Component.objects.all()[0]
        test_tarball = self.static_dir / "test_artifact_tarball.tar.gz"
        with open(test_tarball, "rb") as file_in:
            component.artifact_tarball.save(
                "test_artifact_tarball.tar.gz", File(file_in)
            )
            component.save()
        url = reverse(
            "component-download-artifact", kwargs={"pk": component.identifier}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "application/gzip")
        self.assertIn("Content-Disposition", response.headers)
