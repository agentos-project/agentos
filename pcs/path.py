from pcs.component import Component
from pcs.repo import Repo


class Path(Component):
    def __init__(self, relative_path: str, repo: Repo):
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

    def get(self):
        return self.repo.get_local_file_path(self.relative_path)
