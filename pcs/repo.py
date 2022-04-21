import abc
import logging
import os
import re
import sys
import uuid
from enum import Enum
from pathlib import Path
from typing import Dict, Tuple, TypeVar, Union

from dulwich import porcelain
from dulwich.errors import NotGitRepository
from dulwich.objectspec import parse_commit
from dulwich.repo import Repo as PorcelainRepo
from pcs.exceptions import BadGitStateException, PythonComponentSystemException
from pcs.github_api_manager import GitHubAPIManager
from pcs.identifiers import ComponentIdentifier, RepoIdentifier
from pcs.registry import InMemoryRegistry, Registry
from pcs.specs import NestedRepoSpec, RepoSpec, RepoSpecKeys, flatten_spec
from pcs.utils import AOS_GLOBAL_REPOS_DIR, clear_cache_path, dulwich_checkout

logger = logging.getLogger(__name__)

# Use Python generics (https://mypy.readthedocs.io/en/stable/generics.html)
T = TypeVar("T")


class RepoType(Enum):
    LOCAL = "local"
    GITHUB = "github"


class Repo(abc.ABC):
    """
    Base class used to encapsulate information about where a Component
    is located.
    """
    GITHUB_API = GitHubAPIManager()

    def __init__(self, identifier: str, default_version: str = None):
        self.identifier = identifier
        self._default_version = default_version

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Repo):
            return self.to_spec() == other.to_spec()
        return self == other

    def __contains__(self, item):
        return self.get_local_file_path(str(item)).exists()

    @property
    def default_version(self):
        return self._default_version

    @default_version.setter
    def default_version(self, value: str):
        assert value, "default_version cannot be None or ''"
        self._default_version = value

    @staticmethod
    def from_spec(spec: NestedRepoSpec, base_dir: str = None) -> "Repo":
        flat_spec = flatten_spec(spec)
        if flat_spec[RepoSpecKeys.TYPE] == RepoType.LOCAL.value:
            return LocalRepo.from_spec(spec, base_dir)
        if flat_spec[RepoSpecKeys.TYPE] == RepoType.GITHUB.value:
            return GitHubRepo.from_spec(spec)
        raise PythonComponentSystemException(
            f"Unknown repo type '{flat_spec[RepoSpecKeys.TYPE]} in "
            f"repo '{flat_spec[RepoSpecKeys.IDENTIFIER]}'"
        )

    @classmethod
    def from_registry(
        cls, registry: Registry, identifier: RepoIdentifier
    ) -> "Repo":
        return cls.from_spec(registry.get_repo_spec(identifier))

    @classmethod
    def from_github(
        cls, github_account: str, repo_name: str, identifier: str = None
    ) -> "GitHubRepo":
        if not identifier:
            identifier = f"{github_account}__{repo_name}"
        url = f"https://github.com/{github_account}/{repo_name}"
        return GitHubRepo(identifier, url)

    def clear_repo_cache(
        repo_cache_path: Path = None, assume_yes: bool = False
    ) -> None:
        """
        Completely removes all the repos that have been created or checked
        out in the ``repo_cache_path``. Pass True to ``assume_yes`` to run
        non-interactively.
        """
        repo_cache_path = repo_cache_path or AOS_GLOBAL_REPOS_DIR
        clear_cache_path(repo_cache_path, assume_yes)

    @abc.abstractmethod
    def to_spec(self, flatten: bool = False) -> RepoSpec:
        return NotImplementedError  # type: ignore

    def to_registry(
        self,
        registry: Registry = None,
        recurse: bool = True,  # Leave for compatibility w/ future unified spec
        force: bool = False,
    ) -> Registry:
        if not registry:
            registry = InMemoryRegistry()
        repo_spec = registry.get_repo_spec(
            self.identifier, error_if_not_found=False
        )
        if repo_spec:
            if not force:
                assert repo_spec == self.to_spec(), (
                    f"A Repo with identifier '{self.identifier}' "
                    f"already exists in registry '{registry}' that differs "
                    f"from the one provided."
                    f"New repo spec:\n{self.to_spec()}\n\n"
                    f"Existing repo spec:\n{repo_spec}"
                )
        else:
            registry.add_repo_spec(self.to_spec())
        return registry

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
        Given a path to a Component, this returns a git hash and GitHub repo
        URL where the current version of the Component is publicly accessible.
        This will raise an exception if any of the following checks are true:

        1. The Component is not in a git repo.
        2. The origin of this repo is not GitHub.
        3. The current local branch and corresponding remote branch are not at
           the same commit.
        4. There are uncommitted changes locally


        If ''force'' is True, checks 2, 3, and 4 above are ignored.
        """
        full_path = self.get_local_file_path(
            file_path, component_identifier.version
        )
        assert full_path.exists(), f"Path {full_path} does not exist"
        try:
            self.porcelain_repo = PorcelainRepo.discover(full_path)
        except NotGitRepository:
            raise BadGitStateException(
                f"No git repo with Component found: {full_path}"
            )

        self._check_for_local_changes(force)
        url = self._check_for_github_url(force)
        curr_head_hash = self._check_remote_branch_status(force)
        self.porcelain_repo = None
        return url, curr_head_hash

    def _check_for_github_url(self, force: bool) -> str:
        url = self._get_remote_url(force)
        if url is None or "github.com" not in url:
            error_msg = f"Remote must be on github, not {url}"
            if force:
                print(f"Warning: {error_msg}")
            else:
                raise BadGitStateException(error_msg)
        return url

    def _get_remote_url(self, force: bool, remote_name: str = "origin"):
        url = None
        try:
            REMOTE_KEY = (b"remote", remote_name.encode())
            url = self.porcelain_repo.get_config()[REMOTE_KEY][b"url"].decode()
            # remote, url = porcelain.get_remote_repo(self.porcelain_repo)
        except KeyError:
            error_msg = "Could not find remote repo"
            if force:
                print(f"Warning: {error_msg}")
            else:
                raise BadGitStateException(error_msg)
        return url

    def _get_github_project_and_repo_name(self, url: str):
        """
        Parses a github url of forms:
            * git@github.com:{project_name}/{repo_name}.git
            * https://github.com/{project_name}/{repo_name}.git
        And returns the project_name and repo_name.
        """
        assert url.endswith(".git")
        url = url[:-4]
        if url.startswith("git@github.com:"):
            github_path = url.split(":")[1]
            project_name, repo_name = github_path.split("/")
        else:
            assert url.startswith("https://github.com/")
            project_name, repo_name = url.split("/")[-2:]

        return project_name, repo_name

    def _check_remote_branch_status(self, force: bool) -> str:
        curr_head_hash = self.porcelain_repo.head().decode()
        url = self._get_remote_url(force)
        project_name, repo_name = self._get_github_project_and_repo_name(url)
        remote_commit_exists = self.GITHUB_API.sha1_hash_exists(project_name, repo_name, curr_head_hash)
        if not remote_commit_exists:
            error_msg = (
                f"Current head hash {curr_head_hash} in "
                f"PCS repo {self.local_repo_path} is not on remote {url}. "
                "Push your changes to your remote!"
            )
            if force:
                print(f"Warning: {error_msg}")
            else:
                raise BadGitStateException(error_msg)
        return curr_head_hash

    def _check_for_local_changes(self, force: bool) -> None:
        # Adapted from
        # https://github.com/dulwich/dulwich/blob/master/dulwich/porcelain.py#L1200
        # 1. Get status of staged
        tracked_changes = porcelain.get_tree_changes(self.porcelain_repo)
        # 2. Get status of unstaged
        index = self.porcelain_repo.open_index()
        normalizer = self.porcelain_repo.get_blob_normalizer()
        filter_callback = normalizer.checkin_normalize
        unstaged_changes = list(
            porcelain.get_unstaged_changes(
                index, self.porcelain_repo.path, filter_callback
            )
        )

        uncommitted_changes_exist = (
            len(unstaged_changes) > 0
            or len(tracked_changes["add"]) > 0
            or len(tracked_changes["delete"]) > 0
            or len(tracked_changes["modify"]) > 0
        )
        if uncommitted_changes_exist:
            print(
                f"\nUncommitted changes: {tracked_changes} or "
                f"{unstaged_changes}\n"
            )
            error_msg = "Commit all changes before freezing"
            if force:
                print(f"Warning: {error_msg}")
            else:
                raise BadGitStateException(error_msg)

    def get_prefixed_path_from_repo_root(
        self, identifier: ComponentIdentifier, file_path: str
    ) -> Path:
        """
        Finds the 'component_path' relative to the repo containing the
        Component.  For example, if ``component_path`` is::

            /foo/bar/baz/my_component.py

        and a git repo lives in::

            /foo/bar/.git/

        then this would return::

            baz/my_component.py
        """
        full_path = self.get_local_file_path(file_path, identifier.version)
        name = full_path.name
        curr_path = full_path.parent
        path_prefix = Path()
        while curr_path != Path(curr_path.root):
            try:
                PorcelainRepo(curr_path)
                return path_prefix / name
            except NotGitRepository:
                path_prefix = curr_path.name / path_prefix
                curr_path = curr_path.parent
        raise BadGitStateException(f"Unable to find repo: {full_path}")


class GitHubRepo(Repo):
    """
    A Component with an GitHubRepo can be found on GitHub.
    """

    FULL_GIT_SHA1_RE = re.compile(r"\b[0-9a-f]{40}\b")

    def __init__(
        self, identifier: str, url: str, default_version: str = "master"
    ):
        super().__init__(identifier, default_version)
        self.type = RepoType.GITHUB
        # https repo link allows for cloning without unlocking your GitHub keys
        url = url.replace("git@github.com:", "https://github.com/")
        self.url = url
        self.org_name, self.project_name = self.url.split("/")[-2:]
        self.local_repo_path = None
        self.porcelain_repo = None

    @classmethod
    def from_spec(cls, spec: NestedRepoSpec) -> "LocalRepo":
        flat_spec = flatten_spec(spec)
        return cls(
            flat_spec[RepoSpecKeys.IDENTIFIER],
            url=flat_spec[RepoSpecKeys.URL],
        )

    def to_spec(self, flatten: bool = False) -> Dict:
        spec = {
            self.identifier: {
                RepoSpecKeys.TYPE: self.type.value,
                RepoSpecKeys.URL: self.url,
            }
        }
        return flatten_spec(spec) if flatten else spec

    def get_local_repo_dir(self, version: str = None) -> Path:
        version = self._get_valid_version(version)
        local_repo_path = self._clone_repo(version)
        self._checkout_version(local_repo_path, version)
        sys.stdout.flush()
        return local_repo_path

    def get_local_file_path(self, file_path: str, version: str = None) -> Path:
        version = self._get_valid_version(version)
        local_repo_path = self.get_local_repo_dir(version)
        return (local_repo_path / file_path).absolute()

    def _get_valid_version(self, version):
        version = version if version else self._default_version
        return self._get_hash_from_version(version)

    def _get_hash_from_version(self, version):
        match = re.match(self.FULL_GIT_SHA1_RE, version)
        if match:
            return match.group(0)
        # See if we're referring to a branch
        branches = self.GITHUB_API.get_branches(
            self.org_name, self.project_name
        )
        for branch in branches:
            if branch["name"] == version:
                return branch["commit"]["sha"]
        # See if we're referring to a tag
        tags = self.GITHUB_API.get_tags(self.org_name, self.project_name)
        for tag in tags:
            if tag["name"] == version:
                return tag["commit"]["sha"]
        error_msg = (
            f"Version {version} is not a full SHA1 hash and was "
            f"also not found in branches or tags"
        )
        raise BadGitStateException(error_msg)

    def _clone_repo(self, version: str) -> Path:
        clone_destination = (
            AOS_GLOBAL_REPOS_DIR / self.org_name / self.project_name / version
        )
        if not clone_destination.exists():
            clone_destination.mkdir(parents=True)
            porcelain.clone(
                source=self.url, target=str(clone_destination), checkout=True
            )
        assert clone_destination.exists(), f"Unable to clone {self.url}"
        return clone_destination

    def _checkout_version(self, local_repo_path: Path, version: str) -> None:
        curr_dir = os.getcwd()
        os.chdir(local_repo_path)
        repo = porcelain.open_repo(local_repo_path)
        treeish = parse_commit(repo, version).sha().hexdigest()
        # Checks for a clean working directory were failing on Windows, so
        # force the checkout since this should be a clean clone anyway.
        dulwich_checkout(repo=repo, target=treeish, force=True)
        os.chdir(curr_dir)


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

    def __init__(self, identifier: str, local_dir: Union[Path, str] = None):
        super().__init__(identifier)
        if not local_dir:
            local_dir = f"{AOS_GLOBAL_REPOS_DIR}/{uuid.uuid4()}"
        self.type = RepoType.LOCAL
        self.local_repo_path = Path(local_dir).absolute()
        if self.local_repo_path.exists():
            assert self.local_repo_path.is_dir(), (
                f"local_dir {self.local_repo_path} passed to "
                f"LocalRepo.__init__() with identifier '{self.identifier}'"
                "exists but is not a dir."
            )
        else:
            self.local_repo_path.mkdir(parents=True, exist_ok=True)
            logger.debug(
                f"Created local_dir {self.local_repo_path} for "
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
        return cls(
            flat_spec[RepoSpecKeys.IDENTIFIER],
            local_dir=local_path,
        )

    def to_spec(self, flatten: bool = False) -> RepoSpec:
        spec = {
            self.identifier: {
                RepoSpecKeys.TYPE: self.type.value,
                RepoSpecKeys.PATH: str(self.local_repo_path),
            }
        }
        return flatten_spec(spec) if flatten else spec

    def get_local_repo_dir(self, version: str = None) -> Path:
        assert version is None, "LocalRepos don't support versioning."
        return self.local_repo_path

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
        return self.local_repo_path / relative_path
