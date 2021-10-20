import os
import subprocess
from pathlib import Path


def run_component_in_dir(
    dir_name,
    venv,
    component_name,
    entry_points=None,
    entry_point_params=None,
    req_file="requirements.txt",
):
    entry_points = entry_points or ["evaluate"]
    if req_file:
        print(f"Installing {req_file} with cwd {dir_name}")
        req_cmd = [venv.python, "-m", "pip", "install", "-r", req_file]
        subprocess.check_call(req_cmd, cwd=dir_name)
    for i, entry_point in enumerate(entry_points):
        params = ""
        if entry_point_params:
            assert len(entry_point_params) == len(entry_points), (
                "If not None, entry_point_params must has same len() "
                "as :entry_points:"
                ""
            )
            params = entry_point_params[i]

        if os.name == "nt":
            run_cmd = (
                f"{Path(venv.bin)}/activate.bat & agentos "
                f"run {component_name} --entry-point {entry_point} {params}"
            )
        else:
            run_cmd = (
                f". {Path(venv.bin)}/activate; agentos "
                f"run {component_name} --entry-point {entry_point} {params}"
            )
        print(
            f"Using CLI to run the following command: {run_cmd} with "
            f"cwd={dir_name}."
        )
        subprocess.check_call(run_cmd, shell=True, cwd=dir_name)
