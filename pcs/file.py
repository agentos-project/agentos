from pcs.component import Component
from pcs.repo import Repo


class File(Component):
    def __init__(self, repo: Repo, path: str, version: str = None):
        """
        :param repo: Repo where this Module's source file can be found. The
            ``file_path`` argument is relative to the root this Repo.
        :param path: Path to Python module file this Module manages.
        :version: Version of file.
        """
        super().__init__()
        self.repo = repo
        self.path = path
        self.version = version
        self.register_attributes(["repo", "path", "version"])
