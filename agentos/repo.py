import os
import sys
import abc
from enum import Enum
from typing import TypeVar, Dict, Tuple, Union
from pathlib import Path
from dulwich import porcelain
from dulwich.repo import Repo as PorcelainRepo
from dulwich.objectspec import parse_ref
from dulwich.objectspec import parse_commit
from dulwich.errors import NotGitRepository

from agentos.exceptions import (
    BadGitStateException,
    PythonComponentSystemException,
)
from agentos.utils import AOS_CACHE_DIR
from agentos.component import ComponentIdentifier
from agentos.specs import RepoSpec, NestedRepoSpec, RepoSpecKeys

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

    def __init__(self, identifier: str):
        self.identifier = identifier

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Repo):
            return self.to_spec() == other.to_spec()
        return self == other

    @staticmethod
    def from_spec(spec: NestedRepoSpec, base_dir: Path = None) -> "Repo":
        assert len(spec) == 1
        for identifier, inner_spec in spec.items():
            repo_type = inner_spec["type"]
            if repo_type == RepoType.LOCAL.value:
                assert (
                    base_dir
                ), "The `base_dir` arg is required for local repos."
                path = Path(base_dir) / inner_spec["path"]
                return LocalRepo(identifier=identifier, local_dir=path)
            elif repo_type == RepoType.GITHUB.value:
                return GitHubRepo(identifier=identifier, url=inner_spec["url"])
        raise PythonComponentSystemException(
            f"Unknown repo spec type '{repo_type} in repo {identifier}"
        )

    @abc.abstractmethod
    def to_spec(self, flatten: bool = False) -> RepoSpec:
        return NotImplementedError  # type: ignore

    def optionally_flatten_spec(self, inner: dict, flatten: bool):
        """
        Helper function for optionally flattening a spec.
        :param inner: the inner dict to flatten or not.
        :param flatten: the flag for whether to flatten this spec.
        :return: a spec that is either flattened or not.
        """
        if flatten:
            inner.update({RepoSpecKeys.IDENTIFIER: self.identifier})
            return inner
        else:
            return {self.identifier: inner}

    @abc.abstractmethod
    def get_local_repo_dir(self, version: str) -> Path:
        raise NotImplementedError()

    @abc.abstractmethod
    def get_local_file_path(self, version: str, file_path: str) -> Path:
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
            component_identifier.version, file_path
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
        url = "unknown_url"
        try:
            remote, url = porcelain.get_remote_repo(self.porcelain_repo)
        except IndexError:
            error_msg = "Could not find remote repo"
            if force:
                print(f"Warning: {error_msg}")
            else:
                raise BadGitStateException(error_msg)
        if url is None or "github.com" not in url:
            error_msg = f"Remote must be on github, not {url}"
            if force:
                print(f"Warning: {error_msg}")
            else:
                raise BadGitStateException(error_msg)
        return url

    def _check_remote_branch_status(self, force: bool) -> str:
        try:
            remote, url = porcelain.get_remote_repo(self.porcelain_repo)
        except IndexError:
            error_msg = "Unable to get remote repo"
            if force:
                print(f"Warning: {error_msg}")
                return "unknown_version"
            else:
                raise BadGitStateException(error_msg)
        REMOTE_GIT_PREFIX = "refs/remotes"
        branch = porcelain.active_branch(self.porcelain_repo).decode("UTF-8")
        full_id = f"{REMOTE_GIT_PREFIX}/{remote}/{branch}".encode("UTF-8")
        refs_dict = self.porcelain_repo.refs.as_dict()
        try:
            curr_remote_hash = refs_dict[full_id].decode("UTF-8")
        except KeyError:
            curr_remote_hash = None

        curr_head_hash = self.porcelain_repo.head().decode("UTF-8")

        if curr_head_hash != curr_remote_hash:
            print(
                f"\nBranch {remote}/{branch} "
                "current commit differs from local:"
            )
            print(f"\t{remote}/{branch}: {curr_remote_hash}")
            print(f"\tlocal/{branch}: {curr_head_hash}\n")
            error_msg = (
                f"Push your changes to {remote}/{branch} before freezing"
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
        Component.  For example, if ``component_path`` is:

        ```
        /foo/bar/baz/my_component.py
        ```

        and a git repo lives in:

        ```
        /foo/bar/.git/
        ```

        then this would return:

        ```
        baz/my_component.py
        ```
        """
        full_path = self.get_local_file_path(identifier.version, file_path)
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

    def __init__(self, identifier: str, url: str):
        super().__init__(identifier)
        self.type = RepoType.GITHUB
        # https repo link allows for cloning without unlocking your GitHub keys
        url = url.replace("git@github.com:", "https://github.com/")
        self.url = url
        self.local_repo_path = None
        self.porcelain_repo = None

    def to_spec(self, flatten: bool = False) -> Dict:
        inner = {
            RepoSpecKeys.TYPE: self.type.value,
            RepoSpecKeys.URL: self.url,
        }
        return self.optionally_flatten_spec(inner, flatten)

    def get_local_repo_dir(self, version: str) -> Path:
        local_repo_path = self._clone_repo(version)
        self._checkout_version(local_repo_path, version)
        sys.stdout.flush()
        return local_repo_path

    def get_local_file_path(self, version: str, file_path: str) -> Path:
        local_repo_path = self.get_local_repo_dir(version)
        return (local_repo_path / file_path).absolute()

    def _clone_repo(self, version: str) -> Path:
        org_name, proj_name = self.url.split("/")[-2:]
        clone_destination = AOS_CACHE_DIR / org_name / proj_name / version
        if not clone_destination.exists():
            clone_destination.mkdir(parents=True)
            porcelain.clone(
                source=self.url, target=str(clone_destination), checkout=True
            )
        assert clone_destination.exists(), f"Unable to clone {self.url}"
        return clone_destination

    def _checkout_version(self, local_repo_path: Path, version: str) -> None:
        to_checkout = version if version else "master"
        curr_dir = os.getcwd()
        os.chdir(local_repo_path)
        repo = porcelain.open_repo(local_repo_path)
        treeish = None
        # Is version a branch name?
        try:
            treeish = parse_ref(repo, f"origin/{to_checkout}")
        except KeyError:
            pass

        # Is version a commit hash (long or short)?
        if treeish is None:
            treeish = parse_commit(repo, to_checkout).sha().hexdigest()

        porcelain.reset(repo=repo, mode="hard", treeish=treeish)
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
            # TODO: check for a global .pcsconfig that defines a default
            #      location for a local repo, which will be used to
            #      write source files created by Component.from_class with
            #      classes that are defined in the REPL.
            # NOTE: We do not use utils.AOS_CACHE_DIR here since this
            #       is not a cache of a remote git repo, rather it is a local
            #       repo that may be the only copy in existence.
            local_dir = "./.pcs_local_repo"
        self.type = RepoType.LOCAL
        self.local_dir = Path(local_dir).absolute()
        if self.local_dir.exists():
            assert self.local_dir.is_dir()
            print(
                f"Confirmed local_dir {self.local_dir} for "
                f"LocalRepo {self.identifier} exists and is a dir."
            )
        else:
            self.local_dir.mkdir(parents=True, exist_ok=True)
            print(
                f"Created local_dir {self.local_dir} for "
                f"LocalRepo {self.identifier}."
            )

    def to_spec(self, flatten: bool = False) -> RepoSpec:
        inner = {
            RepoSpecKeys.TYPE: self.type.value,
            RepoSpecKeys.PATH: str(self.local_dir),
        }
        return self.optionally_flatten_spec(inner, flatten)

    def get_local_repo_dir(self, version: str = None) -> Path:
        assert version is None, "LocalRepos don't support versioning."
        return self.local_dir

    def get_local_file_path(self, version: str, relative_path: str) -> Path:
        if version is not None:
            print(
                "WARNING: version was passed into get_local_path() "
                "on a LocalRepo, which means it is being ignored. "
                "If this is actually a versioned repo, use GithubRepo "
                "or another versioned Repo type."
            )
        return self.local_dir / relative_path
