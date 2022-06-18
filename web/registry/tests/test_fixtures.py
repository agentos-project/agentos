import logging
import os
import sys
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path

from agentos.cli import init, publish, run
# from registry.serializers import ComponentSerializer
from click.testing import CliRunner
from django.test import LiveServerTestCase

from registry.models import Component

logger = logging.getLogger(__name__)

from django.core.management import call_command


@contextmanager
def run_in_temp_dir(test_name=None):
    tmp_dir = Path(tempfile.mkdtemp())
    curr_dir = Path(os.getcwd())
    os.chdir(tmp_dir)
    print(f"Running {test_name} test in {tmp_dir}")
    print(f"{tmp_dir}")
    try:
        yield (curr_dir, tmp_dir)
    finally:
        os.chdir(curr_dir)
        # TODO - cleanup
        shutil.rmtree(tmp_dir)


class FixtureTests(LiveServerTestCase):
    def setUp(self):
        self.runner = CliRunner()

    def _save_existing_mlruns(self, curr_dir, experiment_id="0"):
        mlruns_dir = curr_dir / "mlruns"
        self.assertTrue(mlruns_dir.exists())
        self._mlruns_dst_dir = mlruns_dir / experiment_id
        self._existing_mlruns = os.listdir(self._mlruns_dst_dir)

    def _get_new_mlrun_id(self):
        self.assertTrue(hasattr(self, "_mlruns_dst_dir"))
        self.assertTrue(hasattr(self, "_existing_mlruns"))
        curr_mlruns = os.listdir(self._mlruns_dst_dir)
        new_run_ids = []
        for item in curr_mlruns:
            if item not in self._existing_mlruns:
                new_run_ids.append(item)
        self.assertEqual(len(new_run_ids), 1)
        return new_run_ids[0]

    def test_fixture(self):
        with run_in_temp_dir("test_fixture") as (curr_dir, tmp_dir):
            self._save_existing_mlruns(curr_dir)
            mlruns_dir = curr_dir / "mlruns"
            init_args = [str(tmp_dir)]
            init_result = self.runner.invoke(
                init, init_args, catch_exceptions=False
            )
            # print(init_result.stdout_bytes)
            # print(init_result.stderr_bytes)

            run_args = [
                "agent",
                "--registry-file",
                str(tmp_dir / "components.yaml"),
            ]
            run_result = self.runner.invoke(
                run, run_args, catch_exceptions=False
            )
            self.assertEqual(Component.objects.count(), 0)
            publish_args = [self._get_new_mlrun_id()]
            publish_env = {"LOCAL_SERVER_URL": self.live_server_url}
            publish_result = self.runner.invoke(
                publish, publish_args, env=publish_env, catch_exceptions=False
            )
            self.assertEqual(Component.objects.count(), 18)

            sysout = sys.stdout
            try:
                with open('filename.json', 'w') as fixture_file:
                    sys.stdout = fixture_file
                    call_command('dumpdata', 'registry')
            finally:
                sys.stdout = sysout
            self.assertEqual(0, 1)
