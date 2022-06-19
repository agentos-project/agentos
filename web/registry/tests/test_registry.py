# import yaml
# import json
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
        self.assertFalse(bool(self.run.artifact_tarball))
        url = reverse(
            "run-upload-artifact", kwargs={"pk": self.run.identifier}
        )
        tarball = open(self.static_dir / "test_artifacts.tar.gz", "rb")
        response = self.client.post(url, {"tarball": tarball})
        self.assertEqual(response.status_code, 200)
        self.run.refresh_from_db()
        self.assertTrue(bool(self.run.artifact_tarball))

    def test_run_download_artifact(self):
        with open(self.static_dir / "test_artifacts.tar.gz", "rb") as file_in:
            self.run.artifact_tarball.save(
                "test_artifacts.tar.gz", File(file_in)
            )
            self.run.save()
        url = reverse(
            "run-download-artifact", kwargs={"pk": self.run.identifier}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "application/gzip")
        self.assertIn("Content-Disposition", response.headers)

    # TODO: update this test once we've finished reworking ingest_spec
    #       to be ingest_registry (it is moving out from under the Module
    #       model/view).
    # def test_component_replace(self):
    #     self.assertEqual(Module.objects.count(), 1)
    #     url = reverse("component-ingest-spec")
    #     fail_path = self.static_dir / "test_component_replace_fail.yaml"
    #     fail_response = self.client.post(
    #         url, {"components.yaml": open(fail_path)}
    #     )
    #     self.assertEqual(fail_response.status_code, 400)
    #     self.assertEqual(Module.objects.count(), 1)
    #     component = Module.objects.get(id=self.component.id)
    #     self.assertEqual(self.component.repo.id, component.repo.id)
    #     self.assertEqual(self.component.file_path, component.file_path)
    #     self.assertEqual(self.component.name, component.name)
    #     self.assertEqual(self.component.instantiate, component.instantiate)
    #     success_path = (
    #        self.static_dir / "test_component_replace_success.yaml"
    #     )
    #     success_response = self.client.post(
    #         url, {"components.yaml": open(success_path)}
    #     )
    #     self.assertEqual(success_response.status_code, 200)
    #     self.assertEqual(Module.objects.count(), 2)
