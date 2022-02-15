import os
import sys
import yaml
import shutil
import hashlib
import sysconfig
import subprocess
from pathlib import Path

from agentos.registry import Registry
from agentos.utils import AOS_REQS_DIR
from agentos.identifiers import ComponentIdentifier
from agentos.specs import unflatten_spec


class VirtualEnvManager:
    """
    This class manages the Python environment in which a DAG of Components
    runs. The manager provides methods to setup, enable, and disable a virtual
    environment as well as utility methods such as one to clear the whole
    virtual environment cache.

    Due to limitations of the current implementation, a single
    VirtualEnvManager is created per Python runtime (when Component is
    imported).  Thus, environment management may unexpectedly fail if you're
    working with multiple Component DAGs on, say, the REPL.
    """

    def __init__(self):
        self._save_default_env_info()
        self.use_venv = True
        self.venv_path = None
        self._saved_venv_sys_path = None

        self._venv_is_active = False
        self.set_env_cache_path(AOS_REQS_DIR)
        self._py_version = f"python{sysconfig.get_python_version()}"

    def set_environment_handling(self, use_venv: bool) -> None:
        """
        Enables or disables virtual environment management.  If ``use_venv`` is
        set to False, all public methods of this class will be no-ops.
        """
        self.use_venv = use_venv

    def set_env_cache_path(self, env_cache_path: Path) -> None:
        """
        Allows overriding of the path of the environment cache. The environment
        cache is where all the virtual environments for Components are created.
        """
        self._env_cache_path = env_cache_path

    def clear_env_cache(self, assume_yes: bool = False) -> None:
        """
        Completely removes all the virtual environments that have been created
        for Components.  Pass True to ``assume_yes`` to run non-interactively.
        """
        answer = None
        if assume_yes:
            answer = "y"
        else:
            answer = input(
                f"This will remove everything under {self._env_cache_path}.  "
                "Continue? [Y/N] "
            )
        if assume_yes or answer.lower() in ["y", "yes"]:
            shutil.rmtree(self._env_cache_path)
            print("Cache cleared...")
            return
        print("Aborting...")

    def _save_default_env_info(self):
        self._default_sys_path = [p for p in sys.path]
        self._default_sys_prefix = sys.prefix
        self._default_sys_exec_prefix = sys.exec_prefix
        self._default_os_virtual_env = os.environ.get("VIRTUAL_ENV")
        self._default_os_path = os.environ.get("PATH")
        self._default_os_underscore = os.environ.get("_")

    def activate_venv(self) -> None:
        """
        Activates the virtual environment currently being managed. When
        activated, an import statement (e.g. run by a Component) will execute
        within the virtual environment.
        """
        if not self.venv_path or not self.use_venv:
            print("VirtualEnvManager: Running in outer Python environment")
            return
        self._set_venv_sys_path()
        self._set_venv_sys_attributes()
        self._set_venv_sys_environment()
        self._venv_is_active = True
        print(f"VirtualEnvManager: Running in Python venv at {self.venv_path}")

    def _set_venv_sys_path(self):
        sys_path_copy = [p for p in sys.path]
        self._clear_sys_path()
        for p in sys_path_copy:
            if p.startswith(sys.base_prefix):
                sys.path.append(p)
        if sys.platform in ["win32", "win64"]:
            sys.path.insert(0, str(self.venv_path / "Scripts"))
            sys.path.append(str(self.venv_path / "Lib" / "site-packages"))
        else:
            sys.path.insert(0, str(self.venv_path / "bin"))
            versioned_lib_path = self.venv_path / "lib" / self._py_version
            sys.path.append(str(versioned_lib_path / "site-packages"))

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

    def deactivate_venv(self) -> None:
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

    def create_venv(
        self, registry: Registry, identifier: "ComponentIdentifier"
    ) -> Path:
        """
        Creates a new virtual environment based on the requirements specified
        by the Component DAG rooted by Component ``identifier``.  Every
        ``requirements_path`` specified by a Component in the DAG will be pip
        installed by AgentOS during the creation of the virtual environment.
        If no Component in the DAG specifies a ``requirements_path``, then no
        virtual environment is created and the Component DAG will be run in the
        outer Python environment.  Virtual environments are created in the
        environment cache.
        """
        if not self.use_venv:
            return None
        req_paths = self._get_requirement_file_paths(registry, identifier)
        if not req_paths:
            return None
        return self._create_virtual_env(req_paths)

    def _get_requirement_file_paths(
        self, registry: Registry, identifier: "ComponentIdentifier"
    ) -> set:
        # Prevent circular import
        from agentos.repo import Repo

        component_specs, repo_specs = registry.get_specs_transitively_by_id(
            identifier, flatten=True
        )
        repos = {
            repo_spec["identifier"]: Repo.from_spec(
                unflatten_spec(repo_spec), registry.base_dir
            )
            for repo_spec in repo_specs
        }

        req_paths = set()
        for c_spec in component_specs:
            if "requirements_path" not in c_spec:
                continue
            repo = repos[c_spec["repo"]]
            full_req_path = repo.get_local_file_path(
                c_spec["version"], c_spec["requirements_path"]
            ).absolute()
            if not full_req_path.exists():
                error_msg = (
                    f"Requirement path {full_req_path} specified by "
                    f"Component {c_spec} does not exist."
                )
                raise Exception(error_msg)
            req_paths.add(full_req_path)
        return req_paths

    def _create_virtual_env(self, req_paths: set):
        sorted_req_paths = sorted(p for p in req_paths)
        to_hash = hashlib.sha256()
        to_hash.update("empty".encode("utf-8"))
        for req_path in sorted_req_paths:
            with req_path.open() as file_in:
                reqs_data = file_in.read()
                to_hash.update(reqs_data.encode("utf-8"))
        hashed = to_hash.hexdigest()
        self.venv_path = self._env_cache_path / self._py_version / hashed

        if not self.venv_path.exists():
            subprocess.run(
                ["virtualenv", "-p", sys.executable, self.venv_path]
            )

            python_path = self.venv_path / "bin" / "python"
            if sys.platform in ["win32", "win64"]:
                python_path = self.venv_path / "Scripts" / "python.exe"
            for req_path in sorted_req_paths:
                cmd = [
                    str(python_path),
                    "-m",
                    "pip",
                    "install",
                    "-r",
                    str(req_path),
                ]
                pip_cli_flags = self._get_pip_cli_flags(req_path)
                for flag, value in pip_cli_flags.items():
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

    def _get_pip_cli_flags(self, req_path: Path) -> dict:
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
