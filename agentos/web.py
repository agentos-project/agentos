import os
import yaml
import json
import mlflow
import pprint
import shutil
import tarfile
import tempfile
import requests
from pathlib import Path
from typing import Dict
from typing import List
from dotenv import load_dotenv
from agentos.utils import MLFLOW_EXPERIMENT_ID

# add USE_LOCAL_SERVER=True to .env to talk to local server
load_dotenv()

AOS_WEB_BASE_URL = "https://aos-web.herokuapp.com"
if os.getenv("USE_LOCAL_SERVER", False) == "True":
    AOS_WEB_BASE_URL = "http://localhost:8000"
AOS_WEB_API_EXTENSION = "/api/v1"

AOS_WEB_API_ROOT = f"{AOS_WEB_BASE_URL}{AOS_WEB_API_EXTENSION}"


def push_component_spec(frozen_spec: Dict) -> Dict:
    url = f"{AOS_WEB_API_ROOT}/components/ingest_spec/"
    data = {"components.yaml": yaml.dump(frozen_spec)}
    response = requests.post(url, data=data)
    response.raise_for_status()
    result = json.loads(response.content)
    print("\nResults:")
    pprint.pprint(result)
    print()
    return result


def push_run_data(run_data: Dict) -> List:
    url = f"{AOS_WEB_API_ROOT}/runs/"
    data = {"run_data": yaml.dump(run_data)}
    response = requests.post(url, data=data)
    response.raise_for_status()
    result = json.loads(response.content)
    return result


def push_run_artifacts(run_id: int, run_artifacts: List) -> List:
    try:
        tmp_dir_path = Path(tempfile.mkdtemp())
        tar_gz_path = tmp_dir_path / f"run_{run_id}_artifacts.tar.gz"
        with tarfile.open(tar_gz_path, "w:gz") as tar:
            for artifact_path in run_artifacts:
                tar.add(artifact_path, arcname=artifact_path.name)
        files = {"tarball": open(tar_gz_path, "rb")}
        url = f"{AOS_WEB_API_ROOT}/runs/{run_id}/upload_artifact/"
        response = requests.post(url, files=files)
        result = json.loads(response.content)
        return result
    finally:
        shutil.rmtree(tmp_dir_path)


def get_run(run_id: int) -> None:
    from agentos.tracker import AgentTracker
    run_url = f"{AOS_WEB_API_ROOT}/runs/{run_id}"
    run_response = requests.get(run_url)
    run_data = json.loads(run_response.content)
    with open("parameter_set.yaml", "w") as param_file:
        param_file.write(yaml.safe_dump(run_data["parameter_set"]))

    root_response = requests.get(run_data["root_link"])
    root_data = json.loads(root_response.content)

    rerun_cmd = (
        f'agentos run {root_data["name"]}=={root_data["version"]} '
        f'--entry-point {run_data["entry_point"]} '
        f"--param-file parameter_set.yaml"
    )
    with open("README.md", "w") as readme_file:
        readme_file.write("## Rerun this agent\n\n```\n")
        readme_file.write(rerun_cmd)
        readme_file.write("\n```")
    spec_url = f"{run_url}/root_spec"
    spec_response = requests.get(spec_url)
    spec_dict = json.loads(spec_response.content)
    with open("agentos.yaml", "w") as file_out:
        file_out.write(yaml.safe_dump(spec_dict))
    try:
        tar_url = f"{run_url}/download_artifact"
        tmp_dir_path = Path(tempfile.mkdtemp())
        requests.get(tar_url)
        tarball_response = requests.get(tar_url)
        tarball_name = "artifacts.tar.gz"
        tarball_path = tmp_dir_path / tarball_name
        with open(tarball_path, "wb") as f:
            f.write(tarball_response.content)
        tar = tarfile.open(tarball_path)
        tar.extractall(path=tmp_dir_path)
        mlflow.start_run(experiment_id=MLFLOW_EXPERIMENT_ID)
        mlflow.set_tag(AgentTracker.RUN_TYPE_TAG, AgentTracker.LEARN_KEY)
        mlflow.log_metric(
            "episode_count", run_data["metrics"]["training_episode_count"]
        )
        mlflow.log_metric(
            "step_count", run_data["metrics"]["training_step_count"]
        )
        mlflow.end_run()
        mlflow.start_run(experiment_id=MLFLOW_EXPERIMENT_ID)
        mlflow.set_tag(AgentTracker.RUN_TYPE_TAG, AgentTracker.RESTORE_KEY)
        for file_name in os.listdir(tmp_dir_path):
            if file_name == tarball_name:
                continue
            file_path = tmp_dir_path / file_name
            mlflow.log_artifact(file_path)
        for name, value in run_data["metrics"].items():
            mlflow.log_metric(name, value)
        mlflow.end_run()
        print("\nRerun agent as follows:")
        print(rerun_cmd)
        print()
    finally:
        shutil.rmtree(tmp_dir_path)
