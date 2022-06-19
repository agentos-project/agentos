import sys

from pcs.component import Component


class PythonRuntime(Component):
    def __init__(self, version: str = None):
        super().__init__()
        py_ver = sys.version_info
        curr_py_ver = f"python{py_ver.major}.{py_ver.minor}.{py_ver.micro}"
        self.version = version if version else curr_py_ver
        self.register_attribute("version")
