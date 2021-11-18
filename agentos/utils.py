from dulwich import porcelain
from dulwich.repo import Repo
from dulwich.errors import NotGitRepository
import pprint
import yaml
import mlflow
import shutil
from pathlib import Path
import tempfile

MLFLOW_EXPERIMENT_ID = "0"

AOS_CACHE_DIR = Path.home() / ".agentos_cache"


def log_data_as_yaml_artifact(name: str, data: dict):
    tmp_dir_path = Path(tempfile.mkdtemp())
    artifact_path = tmp_dir_path / name
    with open(artifact_path, "w") as file_out:
        file_out.write(yaml.safe_dump(data))
    mlflow.log_artifact(artifact_path)
    shutil.rmtree(tmp_dir_path)


def get_prefixed_path_from_repo_root(component_path):
    """
    Finds the 'component_path' relative to the repo containing the Component.
    For example, if ``component_path`` is:

    ```
    /foo/bar/baz/my_component.py
    ```

    and a git repo lives in:

    ```
    /foo/bar/.git/
    ```

    then this would return:

    ```
    baz/my_component.py
    ```
    """
    name = component_path.name
    curr_path = component_path.parent
    path_prefix = Path()
    while curr_path != Path(curr_path.root):
        try:
            Repo(curr_path)
            return path_prefix / name
        except NotGitRepository:
            path_prefix = curr_path.name / path_prefix
            curr_path = curr_path.parent


def get_version_from_git(component_path):
    """
    Given a path to a Component, this returns a git hash and GitHub repo
    URL where the current version of the Component is publicly accessible.
    """
    component_path = Path(component_path).absolute()
    assert component_path.exists(), f"Path {component_path} does not exist"

    try:
        repo = Repo.discover(component_path)
    except NotGitRepository:
        raise Exception(f"No git repo with Component found: {component_path}")

    REMOTE_GIT_PREFIX = "refs/remotes"
    remote, url = porcelain.get_remote_repo(repo)
    branch = porcelain.active_branch(repo).decode("UTF-8")
    full_id = f"{REMOTE_GIT_PREFIX}/{remote}/{branch}".encode("UTF-8")
    curr_remote_hash = repo.refs.as_dict()[full_id].decode("UTF-8")
    curr_head_hash = repo.head().decode("UTF-8")

    if "github.com" not in url:
        raise Exception(f"Remote must be on github, not {url}")

    if curr_head_hash != curr_remote_hash:
        print(f"\nBranch {remote}/{branch} current commit differs from local:")
        print(f"\t{remote}/{branch}: {curr_remote_hash}")
        print(f"\tlocal/{branch}: {curr_head_hash}\n")
        raise Exception(
            f"Push your changes to {remote}/{branch} before pinning"
        )

    # Adapted from
    # https://github.com/dulwich/dulwich/blob/master/dulwich/porcelain.py#L1200
    # 1. Get status of staged
    tracked_changes = porcelain.get_tree_changes(repo)
    # 2. Get status of unstaged
    index = repo.open_index()
    normalizer = repo.get_blob_normalizer()
    filter_callback = normalizer.checkin_normalize
    unstaged_changes = list(
        porcelain.get_unstaged_changes(index, repo.path, filter_callback)
    )

    uncommitted_changes_exist = (
        len(unstaged_changes) > 0
        or len(tracked_changes["add"]) > 0
        or len(tracked_changes["delete"]) > 0
        or len(tracked_changes["modify"]) > 0
    )
    if uncommitted_changes_exist:
        print(
            f"\nUncommitted changes: {tracked_changes} or {unstaged_changes}\n"
        )
        raise Exception("Commit all changes before pinning")

    # If we are here, then:
    #   * The Component is in a git repo
    #   * The origin of this repo is GitHub
    #   * The current local branch and corresponding remote branch are at the
    #     same commit
    #   * There are no uncommitted changes locally
    return url, curr_head_hash


DUMMY_DEV_REGISTRY = {
    "components": {
        "acme_cartpole==nj_registry_2next": {
            "class_name": "CartPole",
            "dependencies": {},
            "file_path": "example_agents/acme_r2d2/../acme_dqn/environment.py",
            "repo": "dev_repo",
        },
        "acme_r2d2_agent==nj_registry_2next": {
            "class_name": "AcmeR2D2Agent",
            "dependencies": {
                "dataset": "acme_r2d2_dataset==nj_registry_2next",
                "environment": "acme_cartpole==nj_registry_2next",
                "network": "acme_r2d2_network==nj_registry_2next",
                "policy": "acme_r2d2_policy==nj_registry_2next",
                "tracker": "acme_tracker==nj_registry_2next",
                "trainer": "acme_r2d2_trainer==nj_registry_2next",
            },
            "file_path": "example_agents/acme_r2d2/agent.py",
            "repo": "dev_repo",
        },
        "acme_r2d2_dataset==nj_registry_2next": {
            "class_name": "ReverbDataset",
            "dependencies": {
                "environment": "acme_cartpole==nj_registry_2next",
                "network": "acme_r2d2_network==nj_registry_2next",
            },
            "file_path": "example_agents/acme_r2d2/dataset.py",
            "repo": "dev_repo",
        },
        "acme_r2d2_network==nj_registry_2next": {
            "class_name": "R2D2Network",
            "dependencies": {
                "environment": "acme_cartpole==nj_registry_2next",
                "tracker": "acme_tracker==nj_registry_2next",
            },
            "file_path": "example_agents/acme_r2d2/network.py",
            "repo": "dev_repo",
        },
        "acme_r2d2_policy==nj_registry_2next": {
            "class_name": "R2D2Policy",
            "dependencies": {
                "dataset": "acme_r2d2_dataset==nj_registry_2next",
                "environment": "acme_cartpole==nj_registry_2next",
                "network": "acme_r2d2_network==nj_registry_2next",
            },
            "file_path": "example_agents/acme_r2d2/policy.py",
            "repo": "dev_repo",
        },
        "acme_r2d2_trainer==nj_registry_2next": {
            "class_name": "R2D2Trainer",
            "dependencies": {
                "dataset": "acme_r2d2_dataset==nj_registry_2next",
                "environment": "acme_cartpole==nj_registry_2next",
                "network": "acme_r2d2_network==nj_registry_2next",
            },
            "file_path": "example_agents/acme_r2d2/trainer.py",
            "repo": "dev_repo",
        },
        "acme_tracker==nj_registry_2next": {
            "class_name": "AcmeTracker",
            "dependencies": {},
            "file_path": "example_agents/acme_r2d2/../acme_dqn/tracker.py",
            "repo": "dev_repo",
        },
        "sb3_cartpole==nj_registry_2next": {
            "class_name": "CartPole",
            "dependencies": {},
            "file_path": "example_agents/sb3_agent/environment.py",
            "repo": "dev_repo",
        },
        "sb3_ppo_agent==nj_registry_2next": {
            "class_name": "SB3PPOAgent",
            "dependencies": {
                "environment": "sb3_cartpole==nj_registry_2next",
                "tracker": "sb3_tracker==nj_registry_2next",
            },
            "file_path": "example_agents/sb3_agent/agent.py",
            "repo": "dev_repo",
        },
        "sb3_tracker==nj_registry_2next": {
            "class_name": "SB3Tracker",
            "dependencies": {},
            "file_path": "example_agents/sb3_agent/tracker.py",
            "repo": "dev_repo",
        },
    },
    "latest_refs": {
        "acme_cartpole": "nj_registry_2next",
        "acme_r2d2_agent": "nj_registry_2next",
        "acme_r2d2_dataset": "nj_registry_2next",
        "acme_r2d2_network": "nj_registry_2next",
        "acme_r2d2_policy": "nj_registry_2next",
        "acme_r2d2_trainer": "nj_registry_2next",
        "acme_tracker": "nj_registry_2next",
        "sb3_cartpole": "nj_registry_2next",
        "sb3_ppo_agent": "nj_registry_2next",
        "sb3_tracker": "nj_registry_2next",
    },
    "repos": {
        "dev_repo": {
            "type": "github",
            "url": "https://github.com/nickjalbert/agentos",
        }
    },
}


def generate_dummy_dev_registry():
    registry = {}
    VERSION_STRING = "nj_registry_2next"
    r2d2 = _handle_acme_r2d2(VERSION_STRING)
    _merge_registry_dict(registry, r2d2)
    sb3 = _handle_sb3_agent(VERSION_STRING)
    _merge_registry_dict(registry, sb3)
    pprint.pprint(registry)
    return registry


def _merge_registry_dict(a, b):
    for key, val in b.items():
        tmp = a.get(key, {})
        tmp.update(val)
        a[key] = tmp


def _handle_sb3_agent(version_string):
    sb3_path_prefix = Path("example_agents") / Path("sb3_agent")
    sb3_rename_map = {
        "agent": f"sb3_ppo_agent=={version_string}",
        "environment": f"sb3_cartpole=={version_string}",
        "tracker": f"sb3_tracker=={version_string}",
    }

    return _handle_agent(sb3_path_prefix, sb3_rename_map)


def _handle_acme_r2d2(version_string):
    r2d2_path_prefix = Path("example_agents") / Path("acme_r2d2")
    r2d2_rename_map = {
        "agent": f"acme_r2d2_agent=={version_string}",
        "dataset": f"acme_r2d2_dataset=={version_string}",
        "environment": f"acme_cartpole=={version_string}",
        "network": f"acme_r2d2_network=={version_string}",
        "policy": f"acme_r2d2_policy=={version_string}",
        "tracker": f"acme_tracker=={version_string}",
        "trainer": f"acme_r2d2_trainer=={version_string}",
    }
    return _handle_agent(r2d2_path_prefix, r2d2_rename_map)


def _handle_agent(path_prefix, rename_map):
    aos_root = Path(__file__).parent.parent
    agent_spec = aos_root / path_prefix / "agentos.yaml"
    with open(agent_spec) as file_in:
        registry = yaml.safe_load(file_in)
    registry["repos"] = {}
    registry["repos"]["dev_repo"] = {
        "type": "github",
        "url": "https://github.com/nickjalbert/agentos",
    }
    renamed = {}
    for component_name, spec in registry.get("components").items():
        spec["repo"] = "dev_repo"
        spec["file_path"] = str(path_prefix / Path(spec["file_path"]))
        renamed[rename_map[component_name]] = spec
        renamed_dependencies = {}
        for attr_name, dep_name in spec.get("dependencies", {}).items():
            renamed_dependencies[attr_name] = rename_map[dep_name]
        spec["dependencies"] = renamed_dependencies
    registry["components"] = renamed
    registry["latest_refs"] = {
        v.split("==")[0]: v.split("==")[1] for v in rename_map.values()
    }
    return registry


if __name__ == "__main__":
    generate_dummy_dev_registry()
