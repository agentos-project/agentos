import abc
import logging
import sys
import uuid
from pathlib import Path
from typing import Tuple, TypeVar

from pcs.git_manager import GitManager
from pcs.identifiers import ComponentIdentifier
from pcs.spec_object import Component
from pcs.specs import NestedRepoSpec, RepoSpecKeys, flatten_spec
from pcs.utils import AOS_GLOBAL_REPOS_DIR, parse_github_web_ui_url

logger = logging.getLogger(__name__)

# Use Python generics (https://mypy.readthedocs.io/en/stable/generics.html)
T = TypeVar("T")


class Repo(abc.ABC, Component):
    """
    Base class used to encapsulate information about where a Component
    is located.
    """
    ATTRIBUTES = ["default_version"]  # default_version is an @property

    GIT = GitManager()

    def __init__(self, default_version: str = None):
        self._default_version = default_version  # see self.default_version()
        super().__init__()

    def __contains__(self, item):
        return self.get_local_file_path(str(item)).exists()

    @property
    def default_version(self):
        return self._default_version

    @default_version.setter
    def default_version(self, value: str):
        assert value, "default_version cannot be None or ''"
        self._default_version = value

    @classmethod
    def from_github(
        cls, github_account: str, repo_name: str, identifier: str = None
    ) -> "GitHubRepo":
        if not identifier:
            identifier = f"{github_account}__{repo_name}"
        url = f"https://github.com/{github_account}/{repo_name}"
        return GitHubRepo(identifier, url)

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

    @abc.abstractmethod
    def get_local_repo_dir(self, version: str = None) -> Path:
        raise NotImplementedError()

    @abc.abstractmethod
    def get_local_file_path(self, file_path: str, version: str = None) -> Path:
        raise NotImplementedError()

    def get_version_from_git(
        self,
        component_identifier: ComponentIdentifier,
        file_path: str,
        force: bool = False,
    ) -> Tuple[str, str]:
        """
        Given a ComponentIdentifier and a path, this returns a GitHub repo
        URL and a git hash.  This URL and hash is where the version (specified
        by the ComponentIdentifier) of the file at ``file_path`` is publicly
        accessible.

        A number of checks are performed during the course of this operation.
        Pass ``force=True`` to make failure of optional checks non-fatal.  see
        ``GitManager.get_public_url_and_hash()`` for more details.
        """
        full_path = self.get_local_file_path(
            file_path, component_identifier.version
        )
        assert full_path.exists(), f"Path {full_path} does not exist"
        return self.GIT.get_public_url_and_hash(full_path, force)

    def get_prefixed_path_from_repo_root(
        self, identifier: ComponentIdentifier, file_path: str
    ) -> Path:
        """
        Finds the ``component_path`` relative to the repo containing the
        Component.  For example, if ``component_path`` is::

            /foo/bar/baz/my_component.py

        and a git repo lives in::

            /foo/bar/.git/

        then this would return::

            baz/my_component.py
        """
        full_path = self.get_local_file_path(file_path, identifier.version)
        return self.GIT.get_prefixed_path_from_repo_root(full_path)


class GitHubRepo(Repo):
    """
    A Component with an GitHubRepo can be found on GitHub.
    """
    ATTRIBUTES = ["url"]

    def __init__(self, url: str, default_version: str = "master"):
        # https repo link allows for cloning without unlocking your GitHub keys
        url = url.replace("git@github.com:", "https://github.com/")
        self.url = url
        self.org_name, self.project_name, _, _ = parse_github_web_ui_url(url)
        super().__init__(default_version)
        self.local_repo_path = None
        self.porcelain_repo = None

    def get_local_repo_dir(self, version: str = None) -> Path:
        version = self._get_valid_version_sha1(version)
        local_repo_path = self.GIT.clone_repo(
            self.org_name, self.project_name, version
        )
        sys.stdout.flush()
        return local_repo_path

    def get_local_file_path(self, file_path: str, version: str = None) -> Path:
        version = self._get_valid_version_sha1(version)
        local_repo_path = self.get_local_repo_dir(version)
        return (local_repo_path / file_path).absolute()

    def _get_valid_version_sha1(self, version):
        version = version if version else self._default_version
        return self.GIT.get_sha1_from_version(
            self.org_name, self.project_name, version
        )


# TODO: Convert LocalRepo to GitRepo and make GitHubRepo a subclass of it
#       So that under the hood all local repos are seamlessly versioned
#       and publishing any component can be super seamless by easily
#       converting a GitRepo to some default GitHubRepo where anything that
#       a user wants to share can be pushed, perhaps something like
#       github.com/my_username/pcs_repo.
class LocalRepo(Repo):
    """
    A Component with a LocalRepo can be found on your local drive.
    """
    ATTRIBUTES = ["path"]

    def __init__(self, path: str = None):
        super().__init__()
        if not path:
            path = f"{AOS_GLOBAL_REPOS_DIR}/{uuid.uuid4()}"
        self.path = path
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

    @classmethod
    def from_spec(
        cls, spec: NestedRepoSpec, base_dir: str = None
    ) -> "LocalRepo":
        flat_spec = flatten_spec(spec)
        local_path = flat_spec[RepoSpecKeys.PATH]
        if base_dir and not Path(local_path).is_absolute():
            local_path = f"{base_dir}/{local_path}"
        spec_obj = super.from_spec(spec)
        spec_obj.path = local_path
        return spec_obj

    def get_local_repo_dir(self, version: str = None) -> Path:
        assert version is None, "LocalRepos don't support versioning."
        return Path(self.path)

    def get_local_file_path(
        self, relative_path: str, version: str = None
    ) -> Path:
        if version is not None:
            print(
                "WARNING: version was passed into get_local_path() "
                "on a LocalRepo, which means it is being ignored. "
                "If this is actually a versioned repo, use GithubRepo "
                "or another versioned Repo type."
            )
        return Path(self.path) / relative_path
