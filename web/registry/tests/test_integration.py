import logging

from django.test import LiveServerTestCase
from registry.models import Component
from registry.tests.utils import (
    FIXTURE_FILE,
    create_test_fixture,
    load_or_create_fixture,
)

from pcs.registry import WebRegistry
from pcs.repo import GitHubRepo

logger = logging.getLogger(__name__)


class IntegrationTestCases(LiveServerTestCase):
    def test_run_and_publish(self):
        FIXTURE_FILE.unlink(missing_ok=True)
        self.assertEqual(Component.objects.count(), 0)
        # Run agent and upload result to web
        create_test_fixture(self.live_server_url)
        self.assertEqual(Component.objects.count(), 20)

    def test_web_registry_integration(self):
        load_or_create_fixture(self.live_server_url)
        # Check WebRegistry mirrors server
        registry = WebRegistry(f"{self.live_server_url}/api/v1")
        self.assertEqual(Component.objects.count(), 20)
        for component in Component.objects.all():
            registry.get_spec(component.identifier, flatten=False)
            registry.get_spec(component.identifier, flatten=True)
        # Add new spec to WebRegistry, make sure it makes it to the server
        gh_url = "https://github.com/chipsalliance/firrtl-spec"
        gh_repo = GitHubRepo(url=gh_url)
        web_gh_repos = Component.objects.filter(identifier=gh_repo.identifier)
        self.assertEqual(web_gh_repos.count(), 0)
        gh_repo.to_registry(registry)
        self.assertEqual(web_gh_repos.count(), 1)
