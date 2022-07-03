import re
import subprocess
import sys
from typing import List, TYPE_CHECKING, Union

from pcs.component import Component
from pcs.utils import PCSException

if TYPE_CHECKING:
    from pathlib import Path
    from pcs.virtual_env import VirtualEnvComponent


class PythonExecutable:
    def __init__(self, path: "Path"):
        self._path = path
        self._version = None  # Set by self.version()

    @property
    def path(self):
        return self._path

    @property
    def version(self):
        if not self._version:
            # TODO(andyk): Support pre-releases, release candidates, etc.
            ver_str = self.exec_python(["--version"]).stdout.decode().strip()
            res = re.search(r"\d+\.\d+\.\d+", ver_str)
            assert res
            self._version = res.group()
        return self._version

    @property
    def major_version(self):
        res = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", self.version)
        assert res, "version must be of the form N.N.N (e.g. 3.9.10)"
        return res.group(1)

    @property
    def minor_version(self):
        res = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", self.version)
        assert res, "version must be of the form N.N.N (e.g. 3.9.10)"
        return res.group(2)

    @property
    def micro_version(self):
        res = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", self.version)
        assert res, "version must be of the form N.N.N (e.g. 3.9.10)"
        return res.group(3)

    def exec_python(self, args: List[str]) -> subprocess.CompletedProcess:
        """
        Executes Python in a new subprocess with the args provided.

        :param args: must be a list of strings, this is one of the two
        accepted formats to `subprocess.Popen()` (the recommended one).
        :return: a subprocess.CompletedProcess.
        """
        assert isinstance(args, List), "args must be either str or sequence."
        cmd = [self.path] + args
        return subprocess.run(cmd, check=True, capture_output=True)


class LocalPythonExecutable(Component, PythonExecutable):
    def __init__(self, path: "Path" = None):
        Component.__init__(self)
        PythonExecutable.__init__(self)
        assert path.is_file()
        self.path = path
        assert self.version()
        self.register_attributes(["path", "version"])  # version is a property.

    @classmethod
    def from_path(cls, path: Union[str, "Path"]):
        return cls(path=str(path))

    @classmethod
    def from_version(cls, version: str):
        # See if the version requested can be found locally,
        # else download the necessary executable.
        return NotImplementedError

    @classmethod
    def from_current_interpreter(cls):
        return cls(path=sys.executable)


class VirtualEnvPythonExecutable(Component, PythonExecutable):
    def __init__(self, virtual_env: "VirtualEnvComponent"):
        self.virtual_env = virtual_env
        self.register_attribute("virtual_env")

    # Overrides PythonExecutable.path
    @property
    def path(self) -> "Path":
        return self.virtual_env.venv_path / "bin" / "python"
