from agentos.repo import Repo, LocalRepo
from agentos.component import Component
from tests.utils import (
    TESTING_GITHUB_ACCOUNT,
    TESTING_GITHUB_REPO,
    TESTING_BRANCH_NAME,
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
        f"{TESTING_GITHUB_ACCOUNT}/{TESTING_GITHUB_REPO}"
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
    assert repo.local_dir == repo_from_reg.local_dir
