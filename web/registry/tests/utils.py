import os
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path

from click.testing import CliRunner
from django.conf import settings
from django.core.management import call_command

from agentos.cli import init, publish, run

FIXTURE_DIR = settings.BASE_DIR / "registry" / "tests" / "fixtures"
FIXTURE_FILE = FIXTURE_DIR / "fixture.json"


@contextmanager
def run_in_temp_dir(description=None):
    tmp_dir = Path(tempfile.mkdtemp())
    curr_dir = Path(os.getcwd())
    os.chdir(tmp_dir)
    print(f"Running {description} in {tmp_dir}")
    try:
        yield (curr_dir, tmp_dir)
    finally:
        os.chdir(curr_dir)
        shutil.rmtree(tmp_dir)


def load_or_create_fixture(server_url):
    if FIXTURE_FILE.exists():
        print(f"Loading fixture at {FIXTURE_FILE}")
        call_command("loaddata", FIXTURE_FILE)
    else:
        create_test_fixture(server_url)


def create_test_fixture(server_url):
    """Runs the default agent and publishes the run to ``server_url``"""
    EXPERIMENT_ID = "0"
    runner = CliRunner()
    with run_in_temp_dir("AOS registry fixture gen") as (curr_dir, tmp_dir):
        # Record existing mlruns
        mlruns_dir = curr_dir / "mlruns"
        mlruns_dir.mkdir(parents=True, exist_ok=True)
        mlruns_dst_dir = mlruns_dir / EXPERIMENT_ID
        existing_mlruns = os.listdir(mlruns_dst_dir)

        # Run init and run the default agent
        init_args = [str(tmp_dir)]
        runner.invoke(init, init_args, catch_exceptions=False)
        run_args = [
            "agent",
            "--registry-file",
            str(tmp_dir / "components.yaml"),
        ]
        runner.invoke(run, run_args, catch_exceptions=False)

        # Get MLflow AgentRun ID so we can publish it
        curr_mlruns = os.listdir(mlruns_dst_dir)
        new_run_ids = []
        for item in curr_mlruns:
            if item not in existing_mlruns:
                run_dir = mlruns_dst_dir / item
                agent_run_tag = run_dir / "tags" / "pcs.is_agent_run"
                if agent_run_tag.exists():
                    new_run_ids.append(item)
        assert len(new_run_ids) == 1, f"Unexpected runs in {mlruns_dst_dir}"

        # Publish the AgentRun
        publish_args = [new_run_ids[0]]
        publish_env = {"LOCAL_SERVER_URL": server_url}
        runner.invoke(
            publish, publish_args, env=publish_env, catch_exceptions=False
        )
        print(f"Creating fixture at {str(FIXTURE_FILE)}")
        with open(FIXTURE_FILE, "w") as fixture_file:
            call_command("dumpdata", "registry", stdout=fixture_file)
