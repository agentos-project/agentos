import abc
import re
import subprocess
import sys
from typing import List, TYPE_CHECKING, Union

from pcs.component import Component
from pcs.utils import PCSException

if TYPE_CHECKING:
    from pathlib import Path as PathlibPath


class PythonExecutable(Component, abc.ABC):
    @property
    @abc.abstractmethod
    def path(self) -> "PathlibPath":
        raise NotImplementedError

    @property
    def version(self):
        #TODO(andyk): Support pre-releases, release candidates, etc.
        execs_version_str = self.exec_python("--version").stdout.strip()
        res = re.search(r"\d+\.\d+\.\d+", execs_version_str)
        assert res
        return res.group()

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

    def exec_python(self, args: Union[List, str]):
        """
        Executes Python in a new subprocess with the args provided.

        :param args: must be the same format as the `args` to
        `subprocess.Popen()`. If `args` is a list, it will have "python"
        prepended. If `args` is a str, it will have "python " prepended.
        :return: a subprocess.CompletedProcess.
        """
        if isinstance(args, List):
            python_plus_args = self.path.get() + args
        elif isinstance(args, str):
            python_plus_args = f"{self.path.get()} {args}"
        else:
            raise PCSException("args must be either str or sequence.")
        return subprocess.run(
            python_plus_args, check=True, capture_output=True
        )

    @classmethod
    def from_path(cls, path: Union[str,"PathlibPath"]):
        return LocalPythonExecutable(path=str(path))

    @classmethod
    def from_version(cls, version: str):
        # See if the version requested can be found locally,
        # else download the necessary executable.
        return NotImplementedError

    @classmethod
    def from_current_interpreter(cls):
        return cls(path=sys.executable)


class LocalPythonExecutable(PythonExecutable):
    def __init__(self, path: "PathlibPath" = None):
        super().__init__()
        assert path.is_file()
        self.path = path
        assert self.version()
        self.register_attributes(["path", "version"])  # version is a property.
