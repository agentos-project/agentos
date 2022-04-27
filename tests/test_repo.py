from pathlib import Path

from pcs.component import Component
from pcs.repo import LocalRepo, Repo
from tests.utils import (
    TESTING_BRANCH_NAME,
    TESTING_GITHUB_ACCOUNT,
    TESTING_GITHUB_REPO,
)


def test_repo_from_github():
    aos_repo = Repo.from_github(TESTING_GITHUB_ACCOUNT, TESTING_GITHUB_REPO)
    agent_component = Component.from_repo(
        aos_repo,
        identifier=f"agent=={TESTING_BRANCH_NAME}",
        file_path="agentos/core.py",
        class_name="Agent",
        instantiate=True,
    )
    assert hasattr(agent_component.get_object(), "evaluate")
    assert agent_component.identifier == f"agent=={TESTING_BRANCH_NAME}"
    assert agent_component.repo.identifier == (
        f"{TESTING_GITHUB_ACCOUNT}__{TESTING_GITHUB_REPO}"
    )

    aos_repo_w_custom_id = Repo.from_github(
        "agentos-project", "agentos", identifier="custom_ident"
    )
    diff_agent_component = Component.from_repo(
        aos_repo_w_custom_id,
        identifier=f"agent=={TESTING_BRANCH_NAME}",
        file_path="agentos/core.py",
        class_name="Agent",
        instantiate=True,
    )
    assert hasattr(diff_agent_component.get_object(), "evaluate")
    assert diff_agent_component.identifier == f"agent=={TESTING_BRANCH_NAME}"
    assert diff_agent_component.repo.identifier == "custom_ident"


def test_local_to_from_registry():
    repo = LocalRepo("test_id")
    reg = repo.to_registry()
    repo_from_reg = Repo.from_registry(reg, "test_id")
    assert repo.identifier == repo_from_reg.identifier
    assert repo.local_repo_path == repo_from_reg.local_repo_path


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
