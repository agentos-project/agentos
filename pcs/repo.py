import abc
import logging
import sys
import uuid
from pathlib import Path
from typing import Tuple, TypeVar

from pcs.component import Component
from pcs.git_manager import GitManager
from pcs.path import Path as PathComponent
from pcs.utils import AOS_GLOBAL_REPOS_DIR, parse_github_web_ui_url
from pcs.virtual_env import VirtualEnv

logger = logging.getLogger(__name__)

# Use Python generics (https://mypy.readthedocs.io/en/stable/generics.html)
T = TypeVar("T")


class Repo(Component, PathComponent):
    """
    Base class for Components that represent a filestore that files can be
    retrieved from.
    """

    GIT = GitManager()

    @abc.abstractmethod
    def get_local_file_path(self, relative_path: str) -> Path:
        raise NotImplementedError()

    def get(self) -> Path:
        return self.get_local_file_path(".")

    def __contains__(self, item):
        return self.get_local_file_path(str(item)).exists()

    @classmethod
    def from_github(
        cls, github_account: str, repo_name: str, version: str = None
    ) -> "GitRepo":
        url = f"https://github.com/{github_account}/{repo_name}"
        return GitRepo(url, version=version)

    @classmethod
    def clear_repo_cache(
        cls, repo_cache_path: Path = None, assume_yes: bool = False
    ) -> None:
        """
        Completely removes all the repos that have been created or checked
        out in the ``repo_cache_path``. Pass True to ``assume_yes`` to run
        non-interactively.
        """
        cls.GIT.clear_repo_cache(repo_cache_path, assume_yes)

    def to_gitrepo(self, force: bool = False) -> "GitRepo":
        repo_url, version = self.get_version_from_git(self.path, force=force)
        return GitRepo(repo_url, version=version)

    def get_version_from_git(
        self,
        file_path: str,
        force: bool = False,
    ) -> Tuple[str, str]:
        """
        Given a file_path return a git hash and GitHub repo URL where the
        current version of the file is publicly accessible.

        A number of checks are performed during the course of this operation.
        Pass ``force=True`` to make failure of optional checks non-fatal.  see
        ``GitManager.get_public_url_and_hash()`` for more details.
        """
        full_path = self.get_local_file_path(file_path)
        assert full_path.exists(), f"Path {full_path} does not exist"
        return self.GIT.get_public_url_and_hash(full_path, force)

    def get_prefixed_path_from_repo_root(self, file_path: str) -> Path:
        """
        Finds the 'module_path' relative to the repo containing the
        Module.  For example, if ``module_path`` is::

            /foo/bar/baz/my_module.py

        and a git repo lives in::

            /foo/bar/.git/

        then this would return::

            baz/my_module.py
        """
        full_path = self.get_local_file_path(file_path)
        return self.GIT.get_prefixed_path_from_repo_root(full_path)


class GitRepo(Repo):
    """
    A GitRepo optionally can be found on GitHub.
    """

    def __init__(self, url: str, version: str = "master"):
        super().__init__()
        # https repo link allows for cloning without unlocking your GitHub keys
        url = url.replace("git@github.com:", "https://github.com/")
        self.url = url
        self.version = version
        self.register_attributes(["url", "version"])
        self.org_name, self.project_name, _, _ = parse_github_web_ui_url(url)
        self.local_repo_path = None
        self.porcelain_repo = None

    def get_local_dir(self) -> Path:
        version = self._get_valid_version_sha1()
        local_repo_path = self.GIT.clone_repo(
            self.org_name, self.project_name, version
        )
        sys.stdout.flush()
        return local_repo_path

    def clone_at_version(self, version: str) -> "GitRepo":
        """Return a new GitRepo at the provided version"""
        if version == self.version:
            return self
        else:
            return self.__class__(self.url, version=version)

    def get_local_file_path(self, file_path: str) -> Path:
        local_repo_path = self.get_local_dir()
        return (local_repo_path / file_path).absolute()

    def _get_valid_version_sha1(self):
        return self.GIT.get_sha1_from_version(
            self.org_name, self.project_name, self.version
        )


# TODO: Convert LocalRepo to GitRepo and make GitRepo a subclass of it
#       So that under the hood all local repos are seamlessly versioned
#       and publishing any component can be super seamless by easily
#       converting a GitRepo to some default GitRepo where anything that
#       a user wants to share can be pushed, perhaps something like
#       github.com/my_username/pcs_repo.
class LocalRepo(Repo):
    """
    A Module with a LocalRepo can be found on your local drive.
    The optional ``relative_path_prefix`` arg allows for relative paths to
    be used. When relative paths are used, they will be relative
    to the value in ``relative_path_prefix``. This allows the registries to
    be loaded from files and the path of the file can be stored
    in ``relative_path_prefix``.
    """

    def __init__(
        self,
        path: str = None,
    ):
        super().__init__()
        if not path:
            path = f"{AOS_GLOBAL_REPOS_DIR}/{uuid.uuid4()}"
        self.path = path
        self.register_attribute("path")
        actually_a_path = Path(path).absolute()
        if actually_a_path.exists():
            assert actually_a_path.is_dir(), (
                f"path {self.path} passed to LocalRepo.__init__() "
                f"with identifier '{self.identifier}' exists but is not a dir."
            )
        else:
            actually_a_path.mkdir(parents=True, exist_ok=True)
            logger.debug(
                f"Created path {self.path} for "
                f"LocalRepo {self.identifier}."
            )

    def get_local_dir(self) -> Path:
        return Path(self.path)

    def get_local_file_path(self, relative_path: str) -> Path:
        return Path(self.path) / relative_path


class VirtualEnvLibRepo(Repo):
    def __init__(self, virtual_env: VirtualEnv):
        super().__init__()
        self.virtual_env = virtual_env
        self.register_attribute("virtual_env")

    def get_local_file_path(self, relative_path: str) -> Path:
        """
        `relative_path` must have the form [./]package_name/path_to_file
        """
        relative_path = Path(relative_path)
        assert not relative_path.is_absolute()
        assert self.virtual_env.path.is_dir()
        package_name = relative_path.parts[0]
        py_dir = (
            f"python{self.virtual_env.python_executable.major_version}."
            f"{self.virtual_env.python_executable.minor_version}"
        )
        pkgs = self.virtual_env.venv_path / "lib" / py_dir / "site-packages"
        for child in pkgs.iterdir():
            if child.name == package_name:
                return child.joinpath(*relative_path.parts[1:])
            elif child.name == f"{package_name}.egg-link":
                with child.open() as f:
                    # For more about the format of "egg links", see https://setuptools.pypa.io/en/latest/deprecated/python_eggs.html#egg-links  # noqa: E501
                    # TODO: deal with the case where this is a relative path.
                    pkg_path = f.readline().strip()
                return Path(pkg_path).joinpath(*relative_path.parts[1:])
        raise FileNotFoundError(
            f"VirtualEnv cannot resolve: {relative_path} not found"
        )
