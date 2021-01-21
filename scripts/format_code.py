"""
Run black code formatter on AgentOS Python files

To use::

  $ python documentation/format_code.py
"""

import os
from subprocess import run
from subprocess import PIPE

from shared import root_dir
from shared import traverse_tracked_files


def format_file(path):
    extension = os.path.splitext(path)[1]
    if extension != ".py":
        return
    cmd = ["black", path]
    out = run(cmd, stdout=PIPE).stdout.decode("utf-8")
    if out:
        print(path)
        print(out)
        print()


traverse_tracked_files(root_dir, format_file)
