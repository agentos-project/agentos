import os
import sys
from enum import Enum
from typing import TypeVar
from pathlib import Path
from dulwich import porcelain
from dulwich.objectspec import parse_commit
from dulwich.objectspec import parse_ref
from agentos.utils import AOS_CACHE_DIR

# Use Python generics (https://mypy.readthedocs.io/en/stable/generics.html)
T = TypeVar("T")


class RepoType(Enum):
    LOCAL = "local"
    GITHUB = "github"
    IN_MEMORY = "in_memory"
    UNKNOWN = "unknown"


class Repo:
    """
    Base class used to encapsulate information about where a Component
    is located.
    """

    @classmethod
    def from_spec(cls, name, spec):
        if spec["type"] == RepoType.LOCAL.value:
            return LocalRepo(name=name, file_path=spec["path"])
        elif spec["type"] == RepoType.GITHUB.value:
            return GitHubRepo(name=name, url=spec["url"])
        elif spec["type"] == RepoType.IN_MEMORY.value:
            return InMemoryRepo()
        elif spec["type"] == RepoType.UNKNOWN.value:
            return UnknownRepo()
        else:
            raise Exception(f"Unknown repo spec type: {spec}")

    def __eq__(self, other):
        return self.to_dict() == other.to_dict()

    def to_dict(self):
        return {"type": self.type.value}

    def get_file_path(self, version):
        raise NotImplementedError()


class UnknownRepo(Repo):
    """
    A fallback; a Component with an UnknownRepo doesn't have a known
    public source.
    """

    def __init__(self, name=None):
        self.name = name if name else "unknown_repo"
        self.type = RepoType.UNKNOWN


class GitHubRepo(Repo):
    """
    A Component with an GitHubRepo can be found on GitHub.
    """

    def __init__(self, name: str, url: str):
        self.name = name
        self.type = RepoType.GITHUB
        url = url.replace("git@github.com:", "https://github.com/")
        self.url = url
        self.local_repo_path = None

    def to_dict(self):
        return {
            "type": self.type.value,
            "url": self.url,
        }

    def get_file_path(self, version):
        local_repo_path = self._clone_repo(version)
        self._checkout_version(local_repo_path, version)
        sys.stdout.flush()
        return local_repo_path

    def _clone_repo(self, version):
        org_name, proj_name = self.url.split("/")[-2:]
        clone_destination = AOS_CACHE_DIR / org_name / proj_name / version
        if not clone_destination.exists():
            clone_destination.mkdir(parents=True)
            porcelain.clone(
                self.url, target=str(clone_destination), checkout=True
            )
        assert clone_destination.exists(), f"Unable to clone {self.url}"
        return clone_destination

    def _checkout_version(self, local_repo_path, version):
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


class LocalRepo(Repo):
    """
    A Component with a LocalRepo can be found on your local drive.
    """

    def __init__(self, name: str, file_path: str):
        self.name = name
        self.type = RepoType.LOCAL
        self.file_path = Path(file_path)

    def to_dict(self):
        return {
            "type": self.type.value,
            "path": str(self.file_path),
        }

    def get_file_path(self, version):
        return self.file_path


class InMemoryRepo(Repo):
    """
    A Component with a InMemoryRepo was created from a class that was
    already loaded into Python.
    """

    def __init__(self, name=None):
        self.name = name if name else "in_memory"
        self.type = RepoType.IN_MEMORY
