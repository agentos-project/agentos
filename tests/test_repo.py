import agentos
from tests.utils import (
    TESTING_GITHUB_ACCOUNT,
    TESTING_GITHUB_REPO,
    TESTING_BRANCH_NAME,
)


def test_repo_from_github():
    aos_repo = agentos.Repo.from_github(
        TESTING_GITHUB_ACCOUNT, TESTING_GITHUB_REPO
    )
    agent_component = agentos.Component.from_repo(
        aos_repo,
        identifier=f"agent=={TESTING_BRANCH_NAME}",
        class_name="Agent",
        file_path="agentos/core.py",
    )
    assert hasattr(agent_component.get_object(), "evaluate")
    assert agent_component.identifier == f"agent=={TESTING_BRANCH_NAME}"
    assert agent_component.repo.identifier == (
        f"{TESTING_GITHUB_ACCOUNT}/{TESTING_GITHUB_REPO}"
    )

    aos_repo_w_custom_id = agentos.Repo.from_github(
        "agentos-project", "agentos", identifier="custom_ident"
    )
    diff_agent_component = agentos.Component.from_repo(
        aos_repo_w_custom_id,
        identifier=f"agent=={TESTING_BRANCH_NAME}",
        class_name="Agent",
        file_path="agentos/core.py",
    )
    assert hasattr(diff_agent_component.get_object(), "evaluate")
    assert diff_agent_component.identifier == f"agent=={TESTING_BRANCH_NAME}"
    assert diff_agent_component.repo.identifier == "custom_ident"
