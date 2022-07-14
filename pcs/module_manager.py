import importlib
import sys
from pathlib import Path
import pytoml
from typing import Any, Dict

from pcs.object_manager import ObjectManager, T
from pcs.registry import Registry
from pcs.repo import GitRepo, Repo
from pcs.utils import (
    PIP_COMMAND,
    parse_github_web_ui_url,
    pipe_and_check_popen,
)
from pcs.virtual_env import VirtualEnv


class Module(ObjectManager):
    """
    A Module is an Abstract Base Class (ABC) that inherits from ObjectManager.
    A PCS Module wraps a Python Module object and provides a
    standard programmatic mechanism for managing the dependencies a Module
    has on other Modules (via import statements).

    Note that because this class inherits from ObjectManager, which is itself
    an ABC, but *does not* provide implementations of ObjectManager's
    abstract methods `get_new_object()` or `freeze()`, that this is therefore
    (implicitly) an ABC as well.
    """

    DUNDER_NAME = "__component__"

    @staticmethod
    def from_github_registry(github_url: str, identifier: str) -> "FileModule":
        """
        This method gets a Module from a registry file found on GitHub.  If
        the registry file contains a LocalRepo, this method automatically
        translates that LocalRepo into a GitRepo.

        The ``github_url`` argument can be found by navigating to the
        registry file on the GitHub web UI.  It should look like the
        following::

            https://github.com/<project>/<repo>/{blob,raw}/<branch>/<path>
        """
        project, repo_name, branch, reg_file_path = parse_github_web_ui_url(
            github_url
        )
        repo = Repo.from_github(project, repo_name)
        registry = Registry.from_file_in_repo(repo, reg_file_path, branch)
        module = FileModule.from_registry(registry, identifier)
        return module

    @staticmethod
    def from_repo(repo: Repo, file_path: str) -> "FileModule":
        full_path = repo.get_local_file_path(file_path)
        assert full_path.is_file(), f"{full_path} does not exist"
        return FileModule(repo=repo, file_path=file_path)

    def _get_object_from_path(self, full_path: Path) -> Any:
        assert full_path.is_file(), f"{full_path} does not exist"
        spec = importlib.util.spec_from_file_location(
            "AOS_MODULE", str(full_path)
        )
        managed_obj = importlib.util.module_from_spec(spec)
        sys.path.insert(0, str(full_path.parent))
        spec.loader.exec_module(managed_obj)
        setattr(managed_obj, "__component__", self)
        return managed_obj


# TODO: Replace use of `repo` and `file_path` args with pcs.Path.Path since
#     pcs.repo.Repo and pcs.path.RelativePath are now sub-types
#     of pcs.Path.Path.
class FileModule(Module):
    def __init__(
        self,
        repo: Repo,
        file_path: str,
        imports: Dict[str, "Module"] = None,
    ):
        """
        :param repo: Repo where this Module's source file can be found. The
            ``file_path`` argument is relative to the root this Repo.
        :param file_path: Path to Python module file this Module manages.
        :param name: Optionally, the name of the class that is being
            managed. If none provided, then by default this is a
            managed Python Module.
        :param imports: Dict from modules found in import statements
            in self's managed_object (i.e. the Python Module that this
            Module Component represents) to a `pcs.Module`.
        """
        super().__init__()
        self.repo = repo
        self.file_path = file_path
        self.imports = imports if imports else {}
        self.register_attributes(["repo", "file_path", "imports"])

    def get_object(self) -> Any:
        """Return managed Python Module."""
        full_path = self.repo.get_local_file_path(self.file_path)
        return self._get_object_from_path(full_path)

    def freeze(self: T) -> T:
        """
        Return a copy of self that has a GitRepo.
        """
        copy_self = self.copy()
        if not isinstance(self.repo, GitRepo):
            try:
                copy_self.repo = copy_self.repo.to_gitrepo()
            except Exception:
                print(
                    f"Failed to convert Repo {self.repo} of type "
                    f"{self.repo.type} (belonging to Module {self}) to a "
                    f"GitRepo"
                )
                raise
        return copy_self


class VirtualEnvModule(Module):
    def __init__(self, name: str, virtual_env: VirtualEnv):
        super().__init__()
        self.name = name
        self.virtual_env = virtual_env
        self.register_attributes(["name", "virtual_env"])

    def get_new_object(self) -> Any:
        self.virtual_env.activate()
        return importlib.import_module(self.name)

    def reset_object(self):
        if self.virtual_env.is_active:
            self.virtual_env.deactivate()
        super().reset_object()

    def freeze(self: T) -> T:
        raise NotImplementedError
