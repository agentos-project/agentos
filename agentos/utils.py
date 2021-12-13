import pprint

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


DUMMY_DEV_REGISTRY_DICT = {
    "components": {
        "acme_cartpole==nj_registry_2next": {
            "class_name": "CartPole",
            "dependencies": {},
            "file_path": "example_agents/acme_r2d2/../acme_dqn/environment.py",
            "repo": "dev_repo",
        },
        "acme_cartpole==master": {
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
