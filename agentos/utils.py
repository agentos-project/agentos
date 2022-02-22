import pprint
import yaml
from pathlib import Path
from typing import Dict


AOS_CACHE_DIR = Path.home() / ".agentos_cache"
AOS_REQS_DIR = AOS_CACHE_DIR / "requirements_cache"
AOS_REPOS_DIR = AOS_CACHE_DIR / "repos_cache"


def parse_github_web_ui_url(github_url: str) -> (str, str, str):
    """
    Parses a GitHub web UI URL of form::

        https://github.com/<project>/<repo>/{blob,raw}/<branch>/<path>

    and returns a 3-tuple of

    1. The repo URL (i.e. the https URL the repo can be cloned from)
    2. The branch_name or commit hash contained in the URL
    3. The path of the file contained in the suffix of the URL
    """
    URL_STARTS_WITH = "https://github.com"
    error_msg = f'URL must start "{URL_STARTS_WITH}", not "{github_url}"'
    assert github_url.startswith(URL_STARTS_WITH), error_msg
    stripped_url = github_url.lstrip(URL_STARTS_WITH)
    split_url = stripped_url.split("/")
    # Split should look like
    # [<project>, <repo>, {blob/raw}, <branch>, <path_1>, <path_2>, ...]
    assert len(split_url) >= 5, f"Can't find required paths in: {github_url}"
    project_name = split_url[0]
    repo_name = split_url[1]
    repo_url = "/".join((URL_STARTS_WITH, project_name, repo_name))
    branch_name = split_url[3]
    repo_path = "/".join(split_url[4:])
    return repo_url, branch_name, repo_path


def generate_dummy_dev_registry(
    version_string: str = "for_tests_dummy_dev_registry",
) -> Dict:
    registry = {}
    r2d2 = _handle_acme_r2d2(version_string)
    _merge_registry_dict(registry, r2d2)
    sb3 = _handle_sb3_agent(version_string)
    _merge_registry_dict(registry, sb3)
    rando = _handle_random_agent(version_string)
    _merge_registry_dict(registry, rando)
    pprint.pprint(registry)
    return registry


def _merge_registry_dict(a, b):
    for key, val in b.items():
        tmp = a.get(key, {})
        tmp.update(val)
        a[key] = tmp


def _handle_agent(path_prefix, rename_map):
    aos_root = Path(__file__).parent.parent
    agent_spec = aos_root / path_prefix / "components.yaml"
    with open(agent_spec) as file_in:
        registry = yaml.safe_load(file_in)
    renamed = {}
    for component_name, spec in registry.get("components").items():
        spec["file_path"] = str(path_prefix / Path(spec["file_path"]))
        if "requirements_path" in spec:
            spec["requirements_path"] = str(
                path_prefix / Path(spec["requirements_path"])
            )
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


def _handle_random_agent(version_string):
    random_path_prefix = Path("example_agents") / Path("random")
    random_rename_map = {
        "agent": f"random_agent=={version_string}",
        "environment": f"random_corridor=={version_string}",
        "policy": f"random_policy=={version_string}",
        "dataset": f"random_dataset=={version_string}",
        "trainer": f"random_trainer=={version_string}",
        "run_manager": f"run_manager=={version_string}",
    }
    return _handle_agent(random_path_prefix, random_rename_map)


def _handle_sb3_agent(version_string):
    sb3_path_prefix = Path("example_agents") / Path("sb3_agent")
    sb3_rename_map = {
        "sb3_agent": f"sb3_ppo_agent=={version_string}",
        "environment": f"sb3_cartpole=={version_string}",
        "SB3AgentRun": f"SB3AgentRun=={version_string}",
    }
    return _handle_agent(sb3_path_prefix, sb3_rename_map)


def _handle_acme_r2d2(version_string):
    r2d2_path_prefix = Path("example_agents") / Path("acme_r2d2")
    r2d2_rename_map = {
        "agent": f"acme_r2d2_agent=={version_string}",
        "dataset": f"acme_r2d2_dataset=={version_string}",
        "environment": f"acme_cartpole=={version_string}",
        "network": f"acme_r2d2_network=={version_string}",
        "TFModelSaver": f"TFModelSaver=={version_string}",
        "policy": f"acme_r2d2_policy=={version_string}",
        "AcmeRun": f"AcmeRun=={version_string}",
        "trainer": f"acme_r2d2_trainer=={version_string}",
    }
    return _handle_agent(r2d2_path_prefix, r2d2_rename_map)


if __name__ == "__main__":
    generate_dummy_dev_registry()
