import importlib
import sys
import uuid
from typing import Dict

from pcs.object_manager import ObjectManager, T
from pcs.registry import Registry
from pcs.repo import GitRepo, Repo
from pcs.utils import parse_github_web_ui_url


class Module(ObjectManager):
    """
    A Module is an object manager. Objects can be Python Modules, Python
    Classes, or Python Class Instances. The Module abstraction provides a
    standard programmatic mechanism for managing dependencies between these
    objects, reproducibly creating/initializing them and executing their
    methods. You can think of methods on a managed object as "managed methods"
    which we call "Entry Points". We call the execution of an Entry Point a
    "Run". Components provide reproducibility by automatically tracking (i.e.,
    logging) all of the parts that make up a Run, including: (1) the code of
    the object being run (i.e., the Module and its Entry Point), (2) the
    full DAG of other objects it depends on (i.e., DAG of other Components),
    (3) the set of arguments (literally a
    :py:func:`pcs.argument_set.ArgumentSet`) used during initialization of
    the managed object and all objects it transitively depends on, and
    (4) the arguments passed to the Entry Point being run.
    """

    DUNDER_NAME = "__component__"

    def __init__(
        self,
        repo: Repo,
        file_path: str,
        imported_modules: Dict[str, "Module"] = None,
    ):
        """
        :param repo: Repo where this Module's source file can be found. The
            ``file_path`` argument is relative to the root this Repo.
        :param file_path: Path to Python module file this Module manages.
        :param name: Optionally, the name of the class that is being
            managed. If none provided, then by default this is a
            managed Python Module.
        :param imported_modules: Dict from modules found in import statements
            in self's managed_object (i.e. the Python Module that this
            Module Component represents) to a `pcs.Module`.
        """
        super().__init__()
        self.repo = repo
        self.file_path = file_path
        self.imported_modules = imported_modules if imported_modules else {}
        self.register_attributes(["repo", "file_path", "imported_modules"])
        self._parent_modules = set()

    @classmethod
    def from_github_registry(
        cls,
        github_url: str,
        identifier: str,
    ) -> "Module":
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
        module = cls.from_registry(registry, identifier)
        return module

    @classmethod
    def from_repo(cls, repo: Repo, file_path: str) -> "Module":
        full_path = repo.get_local_file_path(file_path)
        assert full_path.is_file(), f"{full_path} does not exist"
        return cls(repo=repo, file_path=file_path)

    def get_object(self):
        """Return managed Python Module."""
        full_path = self.repo.get_local_file_path(self.file_path)
        assert full_path.is_file(), f"{full_path} does not exist"
        spec = importlib.util.spec_from_file_location(
            "AOS_MODULE", str(full_path)
        )
        managed_obj = importlib.util.module_from_spec(spec)
        sys.path.insert(0, str(full_path.parent))
        spec.loader.exec_module(managed_obj)
        setattr(managed_obj, "__component__", self)
        return managed_obj

    def _handle_repo_spec(self, repos):
        existing_repo = repos.get(self.repo.name)
        if existing_repo:
            if self.repo.to_dict() != existing_repo:
                self.repo.name = str(uuid.uuid4())
        repos[self.repo.name] = self.repo.to_dict()

    def freeze(self: T, force: bool = False) -> T:
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
