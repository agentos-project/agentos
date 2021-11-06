import os
import mlflow
import subprocess
from pathlib import Path
from utils import DUMMY_DEV_REGISTRY
from component import Component


class Registry:
    def __init__(self):
        self.registry = DUMMY_DEV_REGISTRY
        self.aos_cache_dir = Path.home() / ".agentos_cache"
        self.instantiated_components = {}

    def get_component(self, name):
        if name in self.instantiated_components:
            return self.instantiated_components[name]
        spec = self.registry["components"][name]
        local_repo_path = self._clone_repo(spec["repo"])
        self._checkout_version(local_repo_path, spec["version"])
        file_path = local_repo_path / spec["file_path"]
        component = Component.get_from_file(spec["class_name"], file_path)
        for alias, dep_name in spec["dependencies"].items():
            dep_component = self.get_component(dep_name)
            component.add_dependency(dep_component, alias=alias)
        self.instantiated_components[name] = component
        return component

    def _clone_repo(self, repo_name):
        repo = self.registry["repos"][repo_name]
        assert repo["type"] == "github", f'Uknown repo type: {repo["type"]}'
        org_name, proj_name = repo["url"].split("/")[-2:]
        clone_destination = self.aos_cache_dir / org_name / proj_name
        if not clone_destination.exists():
            cmd = ["git", "clone", repo["url"], clone_destination]
            result = subprocess.run(cmd)
            assert result.returncode == 0, f"Git clone non-zero return: {cmd}"
        assert clone_destination.exists(), f"Unable to clone {repo['url']}"
        return clone_destination

    def _checkout_version(self, repo_path, version_string):
        curr_dir = os.getcwd()
        os.chdir(repo_path)
        cmd = ["git", "checkout", "-q", version_string]
        result = subprocess.run(cmd)
        assert result.returncode == 0, f"FAILED: {cmd} in {repo_path}"
        os.chdir(curr_dir)


if __name__ == "__main__":
    params = {
        "evaluate": {"num_episodes": 50},
        "learn": {"num_episodes": 100},
        "__init__": {
            "discount": 0.99,
            "sequence_length": 13,
            "store_lstm_state": True,
            "replay_period": 40,
            "batch_size": 32,
            "max_replay_size": 500,
            "priority_exponent": 0.6,
            "max_priority_weight": 0.9,
            "epsilon": 0.01,
            "learning_rate": 0.001,
            "target_update_period": 20,
            "adam_epsilon": 0.001,
            "burn_in_length": 2,
            "n_step": 5,
            "min_replay_size": 50,
            "importance_sampling_exponent": 0.2,
            "clip_grad_norm": None,
            "samples_per_insert": 32.0,
        },
    }

    mlflow.start_run()
    registry = Registry()
    component = registry.get_component("acme_r2d2_agent")
    for fn_name, params in params.items():
        component.add_params_to_all(fn_name, params)
    acme_r2d2_agent = component.get_instance()
    acme_r2d2_agent.evaluate(num_episodes=10)
