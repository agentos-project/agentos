import pprint
import yaml
from pathlib import Path

MLFLOW_EXPERIMENT_ID = "0"


DUMMY_DEV_REGISTRY = {
    "components": {
        "acme_cartpole": {
            "class_name": "CartPole",
            "dependencies": {},
            "file_path": "example_agents/acme_r2d2/../acme_dqn/environment.py",
            "repo": "dev_repo",
            "version": "262fa00",
        },
        "acme_r2d2_agent": {
            "class_name": "AcmeR2D2Agent",
            "dependencies": {
                "dataset": "acme_r2d2_dataset",
                "environment": "acme_cartpole",
                "network": "acme_r2d2_network",
                "policy": "acme_r2d2_policy",
                "tracker": "acme_tracker",
                "trainer": "acme_r2d2_trainer",
            },
            "file_path": "example_agents/acme_r2d2/agent.py",
            "repo": "dev_repo",
            "version": "262fa00",
        },
        "acme_r2d2_dataset": {
            "class_name": "ReverbDataset",
            "dependencies": {
                "environment": "acme_cartpole",
                "network": "acme_r2d2_network",
            },
            "file_path": "example_agents/acme_r2d2/dataset.py",
            "repo": "dev_repo",
            "version": "262fa00",
        },
        "acme_r2d2_network": {
            "class_name": "R2D2Network",
            "dependencies": {
                "environment": "acme_cartpole",
                "tracker": "acme_tracker",
            },
            "file_path": "example_agents/acme_r2d2/network.py",
            "repo": "dev_repo",
            "version": "262fa00",
        },
        "acme_r2d2_policy": {
            "class_name": "R2D2Policy",
            "dependencies": {
                "dataset": "acme_r2d2_dataset",
                "environment": "acme_cartpole",
                "network": "acme_r2d2_network",
            },
            "file_path": "example_agents/acme_r2d2/policy.py",
            "repo": "dev_repo",
            "version": "262fa00",
        },
        "acme_r2d2_trainer": {
            "class_name": "R2D2Trainer",
            "dependencies": {
                "dataset": "acme_r2d2_dataset",
                "environment": "acme_cartpole",
                "network": "acme_r2d2_network",
            },
            "file_path": "example_agents/acme_r2d2/trainer.py",
            "repo": "dev_repo",
            "version": "262fa00",
        },
        "acme_tracker": {
            "class_name": "AcmeTracker",
            "dependencies": {},
            "file_path": "example_agents/acme_r2d2/../acme_dqn/tracker.py",
            "repo": "dev_repo",
            "version": "262fa00",
        },
    },
    "repos": {
        "dev_repo": {
            "type": "github",
            "url": "https://github.com/agentos-project/agentos",
        },
        "local_dir": {"path": ".", "type": "local"},
    },
}


def generate_dummy_dev_registry():
    VERSION_STRING = "262fa00"
    R2D2_PATH_PREFIX = Path("example_agents") / Path("acme_r2d2")
    RENAME_MAP = {
        "agent": "acme_r2d2_agent",
        "dataset": "acme_r2d2_dataset",
        "environment": "acme_cartpole",
        "network": "acme_r2d2_network",
        "policy": "acme_r2d2_policy",
        "tracker": "acme_tracker",
        "trainer": "acme_r2d2_trainer",
    }
    aos_root = Path(__file__).parent.parent
    r2d2_spec = aos_root / R2D2_PATH_PREFIX / "agentos.yaml"
    with open(r2d2_spec) as file_in:
        registry = yaml.safe_load(file_in)
    registry.get("repos")["dev_repo"] = {
        "type": "github",
        "url": "https://github.com/agentos-project/agentos",
    }
    renamed = {}
    for component_name, spec in registry.get("components").items():
        assert spec["repo"] == "local_dir"
        spec["repo"] = "dev_repo"
        spec["file_path"] = str(R2D2_PATH_PREFIX / Path(spec["file_path"]))
        spec["version"] = VERSION_STRING
        renamed[RENAME_MAP[component_name]] = spec
        renamed_dependencies = {}
        for alias, dep_name in spec.get("dependencies", {}).items():
            renamed_dependencies[alias] = RENAME_MAP[dep_name]
        spec["dependencies"] = renamed_dependencies
    registry["components"] = renamed
    pprint.pprint(registry)


if __name__ == "__main__":
    generate_dummy_dev_registry()
