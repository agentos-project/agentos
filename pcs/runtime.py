import re
import sys

from pcs.component import Component


class PythonRuntime(Component):
    def __init__(self, version: str = None):
        super().__init__()
        if version:
            res = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", version)
            assert res, "version must be of the form N.N.N (e.g. 3.9.10)"
            self._major_version = res.group(1)
            self._minor_version = res.group(2)
            self._micro_version = res.group(3)
        else:
            self._major_version = sys.version_info[0]
            self._minor_version = sys.version_info[1]
            self._micro_version = sys.version_info[2]
        self.register_attribute("version")

    @property
    def major_version(self):
        return self._major_version

    @property
    def minor_version(self):
        return self._minor_version

    @property
    def micro_version(self):
        return self._micro_version

    @property
    def version(self):
        return (
            f"{self._major_version}."
            f"{self._minor_version}."
            f"{self._micro_version}"
        )