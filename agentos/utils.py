import yaml
import mlflow
import shutil
from pathlib import Path
import tempfile


MLFLOW_EXPERIMENT_ID = "0"

AOS_CACHE_DIR = Path.home() / ".agentos_cache"


def log_data_as_yaml_artifact(name: str, data: dict):
    try:
        tmp_dir_path = Path(tempfile.mkdtemp())
        artifact_path = tmp_dir_path / name
        with open(artifact_path, "w") as file_out:
            file_out.write(yaml.safe_dump(data))
        mlflow.log_artifact(artifact_path)
    finally:
        shutil.rmtree(tmp_dir_path)


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
