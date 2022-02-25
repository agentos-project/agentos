# import yaml
# import json
from pathlib import Path
from django.core.files.base import File
from django.test import TestCase
from django.test import Client
from django.urls import reverse
from registry.models import Component, Repo, Run, RunCommand

# from .static.data import RUN_CREATE_DATA


class RegistryTestCases(TestCase):
    def setUp(self):
        self.client = Client()
        self.repo = Repo.objects.create(
            identifier="test-repo-a38",
            type="github",
            url="https://github.com/example/example",
        )
        self.component = Component.objects.create(
            identifier="test-component-h42==1.0.1",
            name="test-component-h42",
            version="1.0.1",
            repo=self.repo,
            file_path="/foo/bar/baz",
            class_name="TestComponentH42",
            instantiate=True,
        )
        self.run_command = RunCommand.objects.create(
            entry_point="test_entry_pt",
            argument_set={},
            component=self.component,
        )
        self.run = Run.objects.create(
            identifier="sklldfjiekls",
            agent=self.component,
            environment=self.component,
        )
        self.static_dir = Path(__file__).parent / "static"

    # TODO: update these test once we've finished reworking ingest_spec
    #       to be ingest_registry (it is moving out from under the Component
    #       model/view).
    # def test_registry_ingest(self):
    #     self.assertEqual(Component.objects.count(), 1)
    #     self.assertEqual(ComponentDependency.objects.count(), 0)
    #     self.assertEqual(Repo.objects.count(), 1)
    #     # the ingest registry functionalty doesn't live under the Component
    #     # model/viewset anymore so this URL will be different.
    #     url = reverse("component-ingest-registry")
    #     yaml_file = open(self.static_dir / "test_spec_ingest.yaml")
    #     response = self.client.post(url, {"components.yaml": yaml_file})
    #     self.assertEqual(response.status_code, 200)
    #     self.assertEqual(Component.objects.count(), 7)
    #     self.assertEqual(ComponentDependency.objects.count(), 6)
    #     self.assertEqual(Repo.objects.count(), 2)
    #
    # def test_run_create(self):
    #     self.assertEqual(Run.objects.count(), 1)
    #     url = reverse("run-list")
    #     data = {"run_data": yaml.dump(RUN_CREATE_DATA)}
    #     response = self.client.post(url, data)
    #     self.assertEqual(response.status_code, 200)
    #     self.assertEqual(Run.objects.count(), 2)

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
    #       to be ingest_registry (it is moving out from under the Component
    #       model/view).
    # def test_component_replace(self):
    #     self.assertEqual(Component.objects.count(), 1)
    #     url = reverse("component-ingest-spec")
    #     fail_path = self.static_dir / "test_component_replace_fail.yaml"
    #     fail_response = self.client.post(
    #         url, {"components.yaml": open(fail_path)}
    #     )
    #     self.assertEqual(fail_response.status_code, 400)
    #     self.assertEqual(Component.objects.count(), 1)
    #     component = Component.objects.get(id=self.component.id)
    #     self.assertEqual(self.component.repo.id, component.repo.id)
    #     self.assertEqual(self.component.file_path, component.file_path)
    #     self.assertEqual(self.component.class_name, component.class_name)
    #     self.assertEqual(self.component.instantiate, component.instantiate)
    #     success_path = (
    #        self.static_dir / "test_component_replace_success.yaml"
    #     )
    #     success_response = self.client.post(
    #         url, {"components.yaml": open(success_path)}
    #     )
    #     self.assertEqual(success_response.status_code, 200)
    #     self.assertEqual(Component.objects.count(), 2)
