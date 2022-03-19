from django.test import LiveServerTestCase
from registry.models import Component as ComponentModel
from registry.models import Repo as RepoModel
from registry.models import Run as RunModel
from registry.models import RunCommand as RunCommandModel

from agentos.component import Component
from agentos.component_run import ComponentRun
from agentos.registry import WebRegistry
from agentos.run_command import RunCommand
from pcs.repo import Repo
from tests.utils import TESTING_BRANCH_NAME, TESTING_GITHUB_REPO_URL

agentos_repo_spec = {
    "AgentOSRepo": {
        "type": "github",
        "url": TESTING_GITHUB_REPO_URL,
    }
}
agentos_repo = Repo.from_spec(agentos_repo_spec)


class SimpleComponent:
    def __init__(self, init_member=1):
        self.init_member = init_member

    def add_to_init_member(self, i=1):
        return self.init_member + i


class WebRegistryIntegrationTestCases(LiveServerTestCase):
    def setUp(self):
        self.maxDiff = None

    def test_web_registry_top_down(self):
        web_registry = WebRegistry(f"{self.live_server_url}/api/v1")
        simple_component = Component.from_repo(
            agentos_repo,
            identifier=f"SimpleComponent=={TESTING_BRANCH_NAME}",
            file_path="web/registry/tests/test_integration.py",
            class_name="SimpleComponent",
            instantiate=True,
            use_venv=False,
        )
        arg_set = {"SimpleComponent": {"add_to_init_member": {"i": 10}}}
        comp_run = simple_component.run_with_arg_set(
            "add_to_init_member",
            arg_set,
        )
        self.assertEqual(comp_run.return_value, 11)
        comp_run.to_registry(web_registry)

        self.assertEqual(RepoModel.objects.count(), 1)
        self.assertEqual(ComponentModel.objects.count(), 1)
        self.assertEqual(RunCommandModel.objects.count(), 1)
        self.assertEqual(RunModel.objects.count(), 1)

        # Test fetching all of the specs that were recursively added.
        wr_comp_run = ComponentRun.from_registry(
            web_registry,
            comp_run.identifier,
        )
        wr_run_cmd = RunCommand.from_registry(
            web_registry, wr_comp_run.run_command.identifier
        )
        wr_comp = Component.from_registry(
            web_registry, wr_run_cmd.component.identifier, use_venv=False
        )
        wr_repo = Repo.from_registry(web_registry, wr_comp.repo.identifier)
        self.assertEqual(wr_repo.identifier, agentos_repo.identifier)
        self.assertEqual(wr_repo.type, agentos_repo.type)

    def test_web_registry_bottom_up(self):
        web_registry = WebRegistry(f"{self.live_server_url}/api/v1")
        # Test adding a repo_spec.
        web_registry.add_repo_spec(agentos_repo_spec)
        # Test fetching a flattened repo_spec.
        flat_repo_spec = web_registry.get_repo_spec(
            "AgentOSRepo", flatten=True
        )
        self.assertEqual(len(flat_repo_spec), 3)
        self.assertEqual(flat_repo_spec["identifier"], "AgentOSRepo")
        self.assertEqual(flat_repo_spec["type"], "github")
        self.assertEqual(
            flat_repo_spec["url"],
            TESTING_GITHUB_REPO_URL,
        )

        # Test fetching a unflattened (i.e., nested) repo_spec.
        nested_repo_spec = web_registry.get_repo_spec("AgentOSRepo")
        self.assertEqual(nested_repo_spec["AgentOSRepo"]["type"], "github")
        repo = Repo.from_spec(nested_repo_spec)
        self.assertEqual(repo.identifier, "AgentOSRepo")

        # Test adding a component that we generate from the repo.
        simple_component = Component.from_repo(
            repo,
            identifier=f"SimpleComponent=={TESTING_BRANCH_NAME}",
            file_path="web/registry/tests/test_integration.py",
            class_name="SimpleComponent",
            instantiate=True,
            use_venv=False,
        )
        self.assertEqual(simple_component.repo.identifier, "AgentOSRepo")
        simple_dependency = Component.from_repo(
            agentos_repo,
            identifier=f"SimpleDependency=={TESTING_BRANCH_NAME}",
            file_path="web/registry/tests/test_integration.py",
            class_name="SimpleComponent",
            instantiate=True,
            use_venv=False,
        )
        simple_component.add_dependency(simple_dependency, "dep")

        another_dependency = Component.from_repo(
            agentos_repo,
            identifier=f"AnotherDependency=={TESTING_BRANCH_NAME}",
            file_path="web/registry/tests/test_integration.py",
            class_name="SimpleComponent",
            instantiate=True,
            use_venv=False,
        )
        simple_component.add_dependency(another_dependency, "deptwo")

        web_registry.add_component_spec(simple_dependency.to_spec())
        web_registry.add_component_spec(another_dependency.to_spec())
        web_registry.add_component_spec(simple_component.to_spec())

        # Test getting a flattened component (i.e., the one we just added)
        flat_comp_spec = web_registry.get_component_spec(
            name="SimpleComponent", version=TESTING_BRANCH_NAME, flatten=True
        )
        self.assertEqual(flat_comp_spec["name"], "SimpleComponent")
        self.assertEqual(flat_comp_spec["version"], TESTING_BRANCH_NAME)
        self.assertEqual(flat_comp_spec["repo"], "AgentOSRepo")
        self.assertEqual(flat_comp_spec["instantiate"], True)
        self.assertEqual(
            flat_comp_spec["dependencies"],
            {
                "dep": f"SimpleDependency=={TESTING_BRANCH_NAME}",
                "deptwo": f"AnotherDependency=={TESTING_BRANCH_NAME}",
            },
        )

        # Test getting an unflattened component (i.e., the one we just added)
        flat_comp_spec = web_registry.get_component_spec(
            name="SimpleComponent", version=TESTING_BRANCH_NAME, flatten=False
        )
        full_id = f"SimpleComponent=={TESTING_BRANCH_NAME}"
        self.assertEqual(
            flat_comp_spec[full_id]["class_name"],
            "SimpleComponent",
        )
        self.assertEqual(flat_comp_spec[full_id]["repo"], "AgentOSRepo")

        # Test adding a RunCommand
        arg_set = {"SimpleComponent": {"add_to_init_member": {"i": 10}}}
        comp_run = simple_component.run_with_arg_set(
            "add_to_init_member", arg_set
        )
        run_cmd = comp_run.run_command
        web_registry.add_run_command_spec(run_cmd.to_spec())

        # Test getting a RunCommand (i.e., the one we just added)
        run_command_spec = web_registry.get_run_command_spec(
            comp_run.run_command.identifier, flatten=False
        )
        self.assertEqual(
            run_command_spec[run_cmd.identifier]["entry_point"],
            "add_to_init_member",
        )

        # Test adding a Run
        run_spec = comp_run.to_spec()
        web_registry.add_run_spec(run_spec)

        # Test getting a Run (i.e., the one we just added)
        fetched_run_spec = web_registry.get_run_spec(comp_run.identifier)
        self.assertEqual(fetched_run_spec, run_spec)

        # Test Registry.contains_x_spec() functions.
        self.assertTrue(
            web_registry.get_repo_spec("AgentOSRepo", error_if_not_found=False)
        )
        self.assertTrue(
            web_registry.get_component_spec(
                "SimpleComponent", error_if_not_found=False
            )
        )
        self.assertTrue(
            web_registry.get_run_command_spec(
                comp_run.run_command.identifier, error_if_not_found=False
            )
        )
        self.assertTrue(
            web_registry.get_run_spec(
                comp_run.identifier, error_if_not_found=False
            )
        )

    # TODO: add a test that publishes a ComponentRun or Component from the CLI.
    # def test_web_registry_integration_from_cli():
    #     from tests.utils import run_test_command
    #     run_test_command(...)
