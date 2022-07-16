import pprint
from pathlib import Path

from pcs.class_manager import Class
from pcs.component import Component
from pcs.module_manager import FileModule
from pcs.repo import LocalRepo, Repo
from tests.utils import (
    TESTING_BRANCH_NAME,
    TESTING_GITHUB_ACCOUNT,
    TESTING_GITHUB_REPO,
)


def test_repo_from_github():
    aos_repo = Repo.from_github(TESTING_GITHUB_ACCOUNT, TESTING_GITHUB_REPO)
    print(aos_repo.to_spec())
    agent_class = Class(
        name="Agent",
        module=FileModule.from_repo(
            aos_repo,
            version=TESTING_BRANCH_NAME,
            file_path="agentos/core.py",
        ),
    )
    print("===============")
    print(pprint.pprint(agent_class.to_registry().to_dict()))
    assert hasattr(agent_class.get_object(), "evaluate")
    assert agent_class.module.version == TESTING_BRANCH_NAME
    assert agent_class.module.repo.identifier == aos_repo.identifier


def test_local_to_from_registry():
    repo = LocalRepo("test_path")
    reg = repo.to_registry()
    repo_from_reg = Component.from_registry(reg, repo.identifier)
    print(pprint.pprint(repo.to_registry().to_dict()))
    assert repo.identifier == repo_from_reg.identifier
    assert repo.path == repo_from_reg.path


def test_repo_checkout_bug():
    aos_repo = Repo.from_github("agentos-project", "agentos")
    pcs_component_path = Path("pcs") / Path("component.py")
    # pcs/component.py exists in 4e12203
    exists_version = "4e12203faaf84361af9432271e013ddfb927f75d"
    exists_path = aos_repo.get_local_file_path(
        pcs_component_path, version=exists_version
    )
    assert exists_path.exists()
    # pcs/component.py does NOT exist in 07bc713
    not_exists_version = "07bc71358b4360092b58d78f9eee6dc939e90b10"
    not_exists_path = aos_repo.get_local_file_path(
        pcs_component_path, version=not_exists_version
    )
    assert not not_exists_path.exists()
