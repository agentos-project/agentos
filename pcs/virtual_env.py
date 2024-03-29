import logging
import os
import re
import shutil
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import List, Sequence

import yaml

from pcs.component import Component
from pcs.path import Path as PathComponent
from pcs.python_executable import PythonExecutable
from pcs.utils import (
    AOS_GLOBAL_VENV_DIR,
    PIP_COMMAND,
    PCSException,
    PCSVirtualEnvInstallException,
    clear_cache_path,
    pipe_and_check_popen,
)

logger = logging.getLogger(__name__)


class VirtualEnv(Component):
    """
    This class manages a Python virtual environment. It provides methods to
    setup, enable, and disable a virtual environment.
    """

    PCS_REG_FILENAME = "pcs_registry.yaml"

    def __init__(
        self,
        python_version: str = None,
        requirements_files: List[PathComponent] = None,
        local_packages: List[Path] = None,
    ):
        """
        Creates a new virtual environment.

        :param path: the path to the root dir of this venv. If this is None,
            the path will be managed automatically.
        :param python_version: The version of Python to init this venv with.
        :param requirements_files: a sequence of `pcs.path.Path`s
            to be installed into this environment.
        """
        super().__init__()
        self._saved_venv_sys_path = None
        self._venv_is_active = False
        self._python_executable = None  # Set in self.python_executable()
        self._env_cache_path = AOS_GLOBAL_VENV_DIR
        if python_version:
            assert re.fullmatch(r"\d+\.\d+\.\d+", python_version)
        else:
            ver = sys.version_info
            python_version = f"{ver.major}.{ver.minor}.{ver.micro}"
        self.python_version = python_version
        if requirements_files:
            self.requirements_files = requirements_files
        else:
            self.requirements_files = []
        self.local_packages = local_packages if local_packages else []
        self.register_attributes(
            ["python_version", "requirements_files", "local_packages"]
        )
        try:
            self._build_virtual_env()
        except PCSVirtualEnvInstallException as e:
            self._delete_virtual_env()
            raise PCSVirtualEnvInstallException(
                "Creating VirtualEnv failed. Removed VirtualEnv that "
                f"was in bad state: {self.path}"
            ) from e

    @property
    def path(self) -> Path:
        return self._env_cache_path / self.identifier

    @property
    def bin_path(self) -> Path:
        bin_path = self.path / "bin"
        if sys.platform in ["win32", "win64"]:
            bin_path = self.path / "Scripts"
        return bin_path

    @property
    def python_executable(self) -> PythonExecutable:
        if not self._python_executable:
            py_path = self.bin_path / "python"
            if sys.platform in ["win32", "win64"]:
                py_path = self.bin_path / "python.exe"
            assert py_path.exists()
            self._python_executable = PythonExecutable(py_path)
        return self._python_executable

    @property
    def python_path(self) -> Path:
        return self.python_executable.path

    @classmethod
    def from_existing_venv(cls, existing_venv_path: Path) -> "VirtualEnv":
        assert existing_venv_path.exists()
        # TODO: I'm not sure which version of virtualenv added pyenv.cfg.
        assert (
            (
                (existing_venv_path / "bin").exists()
                or (existing_venv_path / "Scripts").exists()
            )
            and (existing_venv_path / "lib").is_dir()
            and (existing_venv_path / "pyvenv.cfg").exists()
        ), f"'{existing_venv_path}' is not a valid virtualenv."
        if existing_venv_path.is_relative_to(AOS_GLOBAL_VENV_DIR):
            reg_file = existing_venv_path / cls.PCS_REG_FILENAME
            assert reg_file.exists(), (
                f"VirtualEnvs that exist within {AOS_GLOBAL_VENV_DIR} should "
                "all have a registry file written within them."
            )
            return Component.from_yaml(reg_file)
        else:
            # TODO: Infer a VirtualEnv Component that represents the existing
            #     VirtualEnv by pip listing it's modules and
            raise NotImplementedError

    def _write_reg_file(self) -> None:
        self.to_yaml_file(str(self.reg_file_path))

    @property
    def reg_file_path(self) -> Path:
        reg_file = self.path / self.PCS_REG_FILENAME
        if reg_file.exists():
            assert reg_file.is_file()
        return reg_file

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
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        """Deactivates the virtual environment on context exit."""
        self.deactivate()

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
        activated, an import statement (e.g. run by a Module) will execute
        within the virtual environment.
        """
        if self._venv_is_active:
            return
        if not self.path.exists():
            self._build_virtual_env()
        self._save_default_env_info()
        self._exec_activate_this_script()
        self._venv_is_active = True
        logger.info(f"VirtualEnv: Running in Python venv at {self.path}")

    @property
    def is_active(self):
        return self._venv_is_active

    def _exec_activate_this_script(self):
        """
        To see how to manually activate a virtual environment in a running
        interpreter, look at the ``activate_this.py` script automatically
        created in the bin directory of a virtual environment.

        For example, if your virtual environment is found at ``/foo/bar/venv``,
        then you can find the script at ``/foo/bar/venv/bin/activate_this.py``.
        """
        scripts_path = self.path / "bin"
        if sys.platform in ["win32", "win64"]:
            scripts_path = self.path / "Scripts"
        activate_script_path = scripts_path / "activate_this.py"
        with open(activate_script_path) as file_in:
            exec(file_in.read(), {"__file__": activate_script_path})

    def _clear_sys_path(self):
        while len(sys.path) > 0:
            sys.path.pop()

    def _set_venv_sys_attributes(self):
        sys.prefix = str(self.path)
        sys.exec_prefix = str(self.path)

    def _set_venv_sys_environment(self):
        os.environ["VIRTUAL_ENV"] = str(self.path)
        venv_bin_path = self.path / "bin"
        os.environ["PATH"] = f'{str(venv_bin_path)}:{os.environ.get("PATH")}'
        os.environ["_"] = f"{str(self.path)}/bin/python"

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

    def _build_virtual_env(self) -> None:
        assert self.path is not None
        if self.path.exists():
            assert self.reg_file_path
        else:
            # Create the Venv
            subprocess.run(
                ["virtualenv", "-p", self.python_version, self.path],
                check=True,
                capture_output=True,
            )
            # Install req files
            req_paths = [p.get() for p in self.requirements_files]
            for req_path in self._sort_req_paths(req_paths):
                self._install_requirements_file(req_path)
            self._write_reg_file()
            # Install local packages
            for pkg_path in self.local_packages:
                self._install_local_package(pkg_path.get())

    def add_requirements_file(self, req_file: PathComponent) -> None:
        self.add_requirements_files([req_file])

    def add_requirements_files(self, req_files: List[PathComponent]) -> None:
        self.requirements_files += req_files
        self._build_virtual_env()

    def _install_requirements_file(
        self,
        req_path: Path,
        pip_flags: dict = None,
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
        install_flag = "-r"
        install_path = str(req_path)
        if req_path.name == "setup.py":
            install_flag = "-e"
            install_path = str(req_path.parent)
        pip_args = ["install", install_flag, install_path]
        embedded_pip_flags = self._get_embedded_pip_flags(req_path)
        for flag, value in embedded_pip_flags.items():
            pip_args.append(flag)
            pip_args.append(value)

        for flag, value in pip_flags.items():
            pip_args.append(flag)
            pip_args.append(value)
        self.bin_path
        try:
            self._exec_pip(pip_args, cwd=req_path.parent)
        except PCSException as e:
            raise PCSVirtualEnvInstallException(
                "Virtualenv install requirements failed."
            ) from e

    def _install_local_package(self, path: Path) -> None:
        self._exec_pip(["install", str(path)])

    def _exec_pip(self, args, **kwargs):
        component_env = {
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),  # win32
            "VIRTUAL_ENV": str(self.path),
            "PATH": f"{str(self.bin_path)}:{os.environ.get('PATH')}",
        }
        prefix_args = [str(self.python_path), "-m", PIP_COMMAND]
        cmd = prefix_args + args
        print(f"Running: {cmd}")
        pipe_and_check_popen(cmd, env=component_env, **kwargs)

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

    @staticmethod
    def _sort_req_paths(req_paths: Sequence) -> list:
        req_paths = set(req_paths)
        return sorted(p for p in req_paths)

    # ------------------------------------------------------------------------
    # The rest of this class (i.e, the code below this point) is functionality
    # specific to automatically managing the location of a virtualenv.
    # ------------------------------------------------------------------------
    @property
    def env_cache_path(self):
        return self._env_cache_path

    @env_cache_path.setter
    def env_cache_path(self, env_cache_path: Path) -> None:
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
        env_cache_path = env_cache_path or AOS_GLOBAL_VENV_DIR
        clear_cache_path(env_cache_path, assume_yes)

    def _delete_virtual_env(self):
        assert self.path.relative_to(AOS_GLOBAL_VENV_DIR), (
            "Cannot delete folders or directories that are not in "
            "{AOS_GLOBAL_VENV_DIR}."
        )
        shutil.rmtree(self.path)


@contextmanager
def auto_revert_venv(
    python_version: str = None,
    requirements_files: List[PathComponent] = None,
):
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
    venv = VirtualEnv(
        python_version=python_version, requirements_files=requirements_files
    )
    venv.activate()
    try:
        yield venv
    finally:
        venv.deactivate()
