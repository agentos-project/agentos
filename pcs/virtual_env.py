import hashlib
import os
import subprocess
import sys
import sysconfig
from contextlib import contextmanager
from pathlib import Path
from typing import Sequence

import yaml

from pcs.utils import AOS_GLOBAL_REQS_DIR, clear_cache_path


class VirtualEnv:
    """
    This class manages a Python virtual environment. It provides methods to
    setup, enable, and disable virtual environments as well as utility methods
    such as one to clear the whole virtual environment cache.
    """

    def __init__(self, venv_path: Path = None):
        self.venv_path = venv_path
        self._saved_venv_sys_path = None
        self._venv_is_active = False
        self.set_env_cache_path(AOS_GLOBAL_REQS_DIR)
        self._py_version = f"python{sysconfig.get_python_version()}"

    def __enter__(self):
        """
        Activates the virtual environment on context entry. Use as follows:

        ```
        venv = VirtualEnv()
        with venv:
            # do something
        ```
        """
        self.activate()

    def __exit__(self, exc_type, exc_value, exc_tb):
        """Deactivates the virtual environment on context exit."""
        self.deactivate()

    @classmethod
    def from_requirements_paths(cls, req_paths: Sequence) -> "VirtualEnv":
        """
        Takes a sequence of full paths to pip-compatible requirements files,
        creates a new virtual environment, installs all those requirements into
        that environment, and then returns a VirtualEnv object corresponding to
        that virtual environment.
        """
        venv = cls()
        if not req_paths:
            print("VirtualEnv: no requirement paths; Running in an empty env!")
        venv._build_virtual_env(req_paths)
        return venv

    def set_env_cache_path(self, env_cache_path: Path) -> None:
        """
        Allows overriding of the path of the environment cache. The environment
        cache is where all the virtual environments for Components are created.
        """
        self._env_cache_path = env_cache_path

    @staticmethod
    def clear_env_cache(
        env_cache_path: Path = None, assume_yes: bool = False
    ) -> None:
        """
        Completely removes all the virtual environments that have been created
        for Components.  Pass True to ``assume_yes`` to run non-interactively.
        """
        env_cache_path = env_cache_path or AOS_GLOBAL_REQS_DIR
        clear_cache_path(env_cache_path, assume_yes)

    def _save_default_env_info(self):
        self._default_sys_path = [p for p in sys.path]
        self._default_sys_prefix = sys.prefix
        self._default_sys_exec_prefix = sys.exec_prefix
        self._default_os_virtual_env = os.environ.get("VIRTUAL_ENV")
        self._default_os_path = os.environ.get("PATH")
        self._default_os_underscore = os.environ.get("_")

    def activate(self) -> None:
        """
        Activates the virtual environment currently being managed. When
        activated, an import statement (e.g. run by a Component) will execute
        within the virtual environment.
        """
        if self._venv_is_active:
            return
        assert self.venv_path.exists(), f"{self.venv_path} does not exist!"
        self._save_default_env_info()
        self._exec_activate_this_script()
        self._venv_is_active = True
        print(f"VirtualEnv: Running in Python venv at {self.venv_path}")

    def _exec_activate_this_script(self):
        """
        To see how to manually activate a virtual environment in a running
        interpreter, look at the ``activate_this.py` script automatically
        created in the bin directory of a virtual environment.

        For example, if your virtual environment is found at ``/foo/bar/venv``,
        then you can find the script at ``/foo/bar/venv/bin/activate_this.py``.
        """
        scripts_path = self.venv_path / "bin"
        if sys.platform in ["win32", "win64"]:
            scripts_path = self.venv_path / "Scripts"
        activate_script_path = scripts_path / "activate_this.py"
        with open(activate_script_path) as file_in:
            exec(file_in.read(), {"__file__": activate_script_path})

    def _clear_sys_path(self):
        while len(sys.path) > 0:
            sys.path.pop()

    def _set_venv_sys_attributes(self):
        sys.prefix = str(self.venv_path)
        sys.exec_prefix = str(self.venv_path)

    def _set_venv_sys_environment(self):
        os.environ["VIRTUAL_ENV"] = str(self.venv_path)
        venv_bin_path = self.venv_path / "bin"
        os.environ["PATH"] = f'{str(venv_bin_path)}:{os.environ.get("PATH")}'
        os.environ["_"] = f"{str(self.venv_path)}/bin/python"

    def deactivate(self) -> None:
        """
        Deactivates the virtual environment (i.e. re-activates the default
        environment under which AgentOS was executed).
        """
        if not self._venv_is_active:
            return
        self._set_default_sys_path()
        self._set_default_sys_attributes()
        self._set_default_sys_environment()
        self._venv_is_active = False

    def _set_default_sys_path(self):
        self._saved_venv_sys_path = [p for p in sys.path]
        self._clear_sys_path()
        for p in self._default_sys_path:
            sys.path.append(p)

    def _set_default_sys_attributes(self):
        sys.prefix = self._default_sys_prefix
        sys.exec_prefix = self._default_sys_exec_prefix

    def _set_default_sys_environment(self):
        if self._default_os_virtual_env:
            os.environ["VIRTUAL_ENV"] = self._default_os_virtual_env
        if self._default_os_path:
            os.environ["PATH"] = self._default_os_path
        if self._default_os_underscore:
            os.environ["_"] = self._default_os_underscore

    def create_virtual_env(self) -> None:
        """
        Creates the directory and objects that back the virtual environment.
        """
        assert self.venv_path is not None
        assert not self.venv_path.exists(), f"{self.venv_path} exists already!"
        subprocess.run(["virtualenv", "-p", sys.executable, self.venv_path])

    def install_requirements_file(
        self, req_path: Path, pip_flags: dict = None
    ) -> None:
        """
        Installs the requirements_file pointed at by `req_path` into the
        virtual environment. ``pip_flags`` is a dictionary of command-line
        flags to pass to pip during the installation, for example:

        ```
        {'-F': 'https://example.com/foo/bar'}
        ```

        results in pip being run with the following command-line flags:

        ```
        pip install .. -F https://example.com/foo/bar
        ```
        """
        pip_flags = pip_flags or {}
        python_path = self.venv_path / "bin" / "python"
        if sys.platform in ["win32", "win64"]:
            python_path = self.venv_path / "Scripts" / "python.exe"

        install_flag = "-r"
        install_path = str(req_path)
        if req_path.name == "setup.py":
            install_flag = "-e"
            install_path = str(req_path.parent)
        cmd = [
            str(python_path),
            "-m",
            "pip",
            "install",
            install_flag,
            install_path,
        ]
        embedded_pip_flags = self._get_embedded_pip_flags(req_path)
        for flag, value in embedded_pip_flags.items():
            cmd.append(flag)
            cmd.append(value)

        for flag, value in pip_flags.items():
            cmd.append(flag)
            cmd.append(value)
        bin_path = self.venv_path / "bin"
        if sys.platform in ["win32", "win64"]:
            bin_path = self.venv_path / "Scripts"
        component_env = {
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),  # win32
            "VIRTUAL_ENV": str(self.venv_path),
            "PATH": f"{str(bin_path)}:{os.environ.get('PATH')}",
        }
        subprocess.run(cmd, env=component_env)

    def _build_virtual_env(self, req_paths: Sequence):
        hashed = self._hash_req_paths(req_paths)
        self.venv_path = self._env_cache_path / self._py_version / hashed
        if not self.venv_path.exists():
            self.create_virtual_env()
            for req_path in self._sort_req_paths(req_paths):
                self.install_requirements_file(req_path)

    def _hash_req_paths(self, req_paths: Sequence) -> str:
        sorted_req_paths = self._sort_req_paths(req_paths)
        to_hash = hashlib.sha256()
        to_hash.update("empty".encode("utf-8"))
        for req_path in sorted_req_paths:
            with req_path.open() as file_in:
                reqs_data = file_in.read()
                to_hash.update(reqs_data.encode("utf-8"))
        return to_hash.hexdigest()

    def _sort_req_paths(self, req_paths: Sequence) -> list:
        req_paths = set(req_paths)
        return sorted(p for p in req_paths)

    def _get_embedded_pip_flags(self, req_path: Path) -> dict:
        """
        Sometimes virtual environments must be created with special flag passed
        to PIP.  This parses a requirement file and finds these flags. Flags
        are specified in a commented out yaml dictionary.  For example, the
        following in a requirements file:

        ```
        # agentos_pip_cmdline:
        #   linux:
        #       "-f": "https://download.pytorch.org/whl/torch_stable.html"
        ```

        will pass `-f https://download.pytorch.org/whl/torch_stable.html` to
        pip when the requirements file is installed on linux platforms.

        The format is as follows:

        ```
        # agentos_pip_cmdline:
        #   <platform>:
        #       <flag_1>: <value_1>
        #       <flag_2>: <value_2>
        ```
        """
        with req_path.open() as file_in:
            req_data = file_in.read()
        PIP_CMDLINE_SIGIL = "agentos_pip_cmdline:"
        found_flags = False
        flag_dict = {}
        flag_lines = []
        for line in req_data.split("\n"):
            if line.startswith("#") and PIP_CMDLINE_SIGIL in line:
                found_flags = True
            if found_flags and not line.startswith("#"):
                found_flags = False
                flag_lines = [fl.lstrip("#") for fl in flag_lines]
                tmp_dict = yaml.safe_load("\n".join(flag_lines))
                platform_dict = tmp_dict[PIP_CMDLINE_SIGIL[:-1]]
                for platform, flags in platform_dict.items():
                    if platform != sys.platform:
                        continue
                    flag_dict.update(flags)
                flag_lines = []
            if found_flags:
                flag_lines.append(line)
        return flag_dict


class NoOpVirtualEnv(VirtualEnv):
    """
    This class implements the VirtualEnv interface, but does not actually
    modify the Python environment in which the program is executing.  Use this
    class anywhere you need a VirtualEnv object but where you also do not want
    to modify the execution environment (i.e. you just want to run code in the
    existing Python environment).
    """

    @classmethod
    def from_requirements_paths(cls, req_paths: Sequence) -> "VirtualEnv":
        return cls()

    def activate(self) -> None:
        print("VirtualEnv: Running in outer Python environment")

    def deactivate(self) -> None:
        pass

    def create_virtual_env(self) -> None:
        pass

    def install_requirements_file(
        self, req_path: Path, pip_flags: dict = None
    ) -> None:
        pass


@contextmanager
def auto_revert_venv():
    """
    Use this context manager when you need to revert the Python environment to
    whatever was in place before the managed block.  Useful in tests when an
    exception might leave the environment in an unexpected state and cause
    spurious test failures.

    Usage example::


        with auto_revert_venv():
            # Do something here that may fail, leaving the env in a bad state
        # Env guaranteed to be reset to its pre-managed-block state here
    """
    venv = VirtualEnv()
    venv._save_default_env_info()
    venv._venv_is_active = True
    try:
        yield
    finally:
        venv.deactivate()
