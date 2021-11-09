import os
import subprocess
from enum import Enum
from typing import TypeVar
from pathlib import Path
from agentos.utils import AOS_CACHE_DIR

# Use Python generics (https://mypy.readthedocs.io/en/stable/generics.html)
T = TypeVar("T")


class RepoType(Enum):
    LOCAL = "local"
    GITHUB = "github"
    IN_MEMORY = "in_memory"
    UNKNOWN = "unknown"


class Repo:
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

    def to_dict(self):
        return {"type": self.type.value}

    def get_file_path(self, version):
        raise NotImplementedError()


class UnknownRepo(Repo):
    def __init__(self, name=None):
        self.name = name if name else "unknown_repo"
        self.type = RepoType.UNKNOWN


class GitHubRepo(Repo):
    def __init__(self, name: str, url: str):
        self.name = name
        self.type = RepoType.GITHUB
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
        return local_repo_path

    def _clone_repo(self, version):
        org_name, proj_name = self.url.split("/")[-2:]
        clone_destination = AOS_CACHE_DIR / org_name / proj_name / version
        if not clone_destination.exists():
            cmd = ["git", "clone", self.url, str(clone_destination)]
            result = subprocess.run(cmd)
            assert result.returncode == 0, f"Git clone non-zero return: {cmd}"
        assert clone_destination.exists(), f"Unable to clone {self.url}"
        return clone_destination

    def _checkout_version(self, local_repo_path, version):
        to_checkout = version if version else "master"
        curr_dir = os.getcwd()
        os.chdir(local_repo_path)
        cmd = ["git", "checkout", "-q", to_checkout]
        result = subprocess.run(cmd)
        assert result.returncode == 0, f"ERR: {cmd} in {local_repo_path}"
        os.chdir(curr_dir)


class LocalRepo(Repo):
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
    def __init__(self, name=None):
        self.name = name if name else "in_memory"
        self.type = RepoType.IN_MEMORY
