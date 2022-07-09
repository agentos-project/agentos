from typing import TYPE_CHECKING
from pcs.component import Component

if TYPE_CHECKING:
    from pathlib import Path as PathlibPath
    from pcs.repo import Repo


class Path(Component):
    def __init__(self, repo: "Repo", relative_path: str):
        """
        :param repo: Repo where this Module's source file can be found. The
            ``file_path`` argument is relative to the root this Repo.
        :param path: Path to Python module file this Module manages.
        :version: Version of file.
        """
        super().__init__()
        self.relative_path = relative_path
        self.repo = repo
        self.register_attributes(["relative_path", "repo"])

    @classmethod
    def from_local_path(cls, path: "PathlibPath"):
        assert path.exists()
        from pcs.repo import LocalRepo  # Avoid circular dependency.

        if path.is_dir():
            return cls(LocalRepo(str(path)), ".")
        else:
            return cls(LocalRepo(str(path.parent)), path.name)

    def get(self) -> "PathlibPath":
        return self.repo.get_local_file_path(self.relative_path)
