import pprint
import yaml
from pathlib import Path


AOS_CACHE_DIR = Path.home() / ".agentos_cache"

DUMMY_DEV_REGISTRY = {
    "components": {
        "acme_cartpole==fe150c5ea8ee6e2e6c1dbbfc85cb53b85f19c55f": {
            "class_name": "CartPole",
            "dependencies": {},
            "file_path": "example_agents/acme_r2d2/../acme_dqn/environment.py",
            "repo": "dev_repo",
        },
        "acme_r2d2_agent==fe150c5ea8ee6e2e6c1dbbfc85cb53b85f19c55f": {
            "class_name": "AcmeR2D2Agent",
            "dependencies": {
                "dataset": "acme_r2d2_dataset==fe150c5ea8ee6e2e6c1dbbfc85cb53b85f19c55f",  # noqa: E501
                "environment": "acme_cartpole==fe150c5ea8ee6e2e6c1dbbfc85cb53b85f19c55f",  # noqa: E501
                "network": "acme_r2d2_network==fe150c5ea8ee6e2e6c1dbbfc85cb53b85f19c55f",  # noqa: E501
                "policy": "acme_r2d2_policy==fe150c5ea8ee6e2e6c1dbbfc85cb53b85f19c55f",  # noqa: E501
                "run_manager": "acme_run_manager==fe150c5ea8ee6e2e6c1dbbfc85cb53b85f19c55f",  # noqa: E501
                "trainer": "acme_r2d2_trainer==fe150c5ea8ee6e2e6c1dbbfc85cb53b85f19c55f",  # noqa: E501
            },
            "file_path": "example_agents/acme_r2d2/agent.py",
            "repo": "dev_repo",
        },
        "acme_r2d2_dataset==fe150c5ea8ee6e2e6c1dbbfc85cb53b85f19c55f": {
            "class_name": "ReverbDataset",
            "dependencies": {
                "environment": "acme_cartpole==fe150c5ea8ee6e2e6c1dbbfc85cb53b85f19c55f",  # noqa: E501
                "network": "acme_r2d2_network==fe150c5ea8ee6e2e6c1dbbfc85cb53b85f19c55f",  # noqa: E501
            },
            "file_path": "example_agents/acme_r2d2/dataset.py",
            "repo": "dev_repo",
        },
        "acme_r2d2_network==fe150c5ea8ee6e2e6c1dbbfc85cb53b85f19c55f": {
            "class_name": "R2D2Network",
            "dependencies": {
                "environment": "acme_cartpole==fe150c5ea8ee6e2e6c1dbbfc85cb53b85f19c55f",  # noqa: E501
                "run_manager": "acme_run_manager==fe150c5ea8ee6e2e6c1dbbfc85cb53b85f19c55f",  # noqa: E501
            },
            "file_path": "example_agents/acme_r2d2/network.py",
            "repo": "dev_repo",
        },
        "acme_r2d2_policy==fe150c5ea8ee6e2e6c1dbbfc85cb53b85f19c55f": {
            "class_name": "R2D2Policy",
            "dependencies": {
                "dataset": "acme_r2d2_dataset==fe150c5ea8ee6e2e6c1dbbfc85cb53b85f19c55f",  # noqa: E501
                "environment": "acme_cartpole==fe150c5ea8ee6e2e6c1dbbfc85cb53b85f19c55f",  # noqa: E501
                "network": "acme_r2d2_network==fe150c5ea8ee6e2e6c1dbbfc85cb53b85f19c55f",  # noqa: E501
            },
            "file_path": "example_agents/acme_r2d2/policy.py",
            "repo": "dev_repo",
        },
        "acme_r2d2_trainer==fe150c5ea8ee6e2e6c1dbbfc85cb53b85f19c55f": {
            "class_name": "R2D2Trainer",
            "dependencies": {
                "dataset": "acme_r2d2_dataset==fe150c5ea8ee6e2e6c1dbbfc85cb53b85f19c55f",  # noqa: E501
                "environment": "acme_cartpole==fe150c5ea8ee6e2e6c1dbbfc85cb53b85f19c55f",  # noqa: E501
                "network": "acme_r2d2_network==fe150c5ea8ee6e2e6c1dbbfc85cb53b85f19c55f",  # noqa: E501
            },
            "file_path": "example_agents/acme_r2d2/trainer.py",
            "repo": "dev_repo",
        },
        "acme_run_manager==fe150c5ea8ee6e2e6c1dbbfc85cb53b85f19c55f": {
            "class_name": "AcmeRunManager",
            "dependencies": {},
            "file_path": "example_agents/acme_r2d2/../acme_dqn/run_manager.py",
            "repo": "dev_repo",
        },
        "sb3_cartpole==fe150c5ea8ee6e2e6c1dbbfc85cb53b85f19c55f": {
            "class_name": "CartPole",
            "dependencies": {},
            "file_path": "example_agents/sb3_agent/environment.py",
            "repo": "dev_repo",
        },
        "sb3_ppo_agent==fe150c5ea8ee6e2e6c1dbbfc85cb53b85f19c55f": {
            "class_name": "SB3PPOAgent",
            "dependencies": {
                "environment": "sb3_cartpole==fe150c5ea8ee6e2e6c1dbbfc85cb53b85f19c55f",  # noqa: E501
                "run_manager": "sb3_run_manager==fe150c5ea8ee6e2e6c1dbbfc85cb53b85f19c55f",  # noqa: E501
            },
            "file_path": "example_agents/sb3_agent/agent.py",
            "repo": "dev_repo",
        },
        "sb3_run_manager==fe150c5ea8ee6e2e6c1dbbfc85cb53b85f19c55f": {
            "class_name": "SB3RunManager",
            "dependencies": {},
            "file_path": "example_agents/sb3_agent/run_manager.py",
            "repo": "dev_repo",
        },
    },
    "latest_refs": {
        "acme_cartpole": "fe150c5ea8ee6e2e6c1dbbfc85cb53b85f19c55f",
        "acme_r2d2_agent": "fe150c5ea8ee6e2e6c1dbbfc85cb53b85f19c55f",
        "acme_r2d2_dataset": "fe150c5ea8ee6e2e6c1dbbfc85cb53b85f19c55f",
        "acme_r2d2_network": "fe150c5ea8ee6e2e6c1dbbfc85cb53b85f19c55f",
        "acme_r2d2_policy": "fe150c5ea8ee6e2e6c1dbbfc85cb53b85f19c55f",
        "acme_r2d2_trainer": "fe150c5ea8ee6e2e6c1dbbfc85cb53b85f19c55f",
        "acme_run_manager": "fe150c5ea8ee6e2e6c1dbbfc85cb53b85f19c55f",
        "sb3_cartpole": "fe150c5ea8ee6e2e6c1dbbfc85cb53b85f19c55f",
        "sb3_ppo_agent": "fe150c5ea8ee6e2e6c1dbbfc85cb53b85f19c55f",
        "sb3_run_manager": "fe150c5ea8ee6e2e6c1dbbfc85cb53b85f19c55f",
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
    VERSION_STRING = "fe150c5ea8ee6e2e6c1dbbfc85cb53b85f19c55f"
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
        "run_manager": f"sb3_run_manager=={version_string}",
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
        "run_manager": f"acme_run_manager=={version_string}",
        "trainer": f"acme_r2d2_trainer=={version_string}",
    }
    return _handle_agent(r2d2_path_prefix, r2d2_rename_map)


def _handle_agent(path_prefix, rename_map):
    aos_root = Path(__file__).parent.parent
    agent_spec = aos_root / path_prefix / "components.yaml"
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
