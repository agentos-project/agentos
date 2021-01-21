"""
Lints AgentOS Python files

To use::

  $ python scripts/lint_code.py
"""

import os
from subprocess import Popen
from subprocess import DEVNULL

scripts_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.normpath(os.path.join(scripts_dir, os.pardir))


def is_git_tracked(file_path):
    cmd = ["git", "ls-files", "--error-unmatch", file_path]
    child = Popen(cmd, stdout=DEVNULL, stderr=DEVNULL)
    child.wait()
    return child.returncode == 0


def traverse_tracked_files(path, action_fn):
    if not is_git_tracked(path):
        return

    if os.path.isfile(path):
        action_fn(path)

    if os.path.isdir(path):
        for item in os.listdir(path):
            to_traverse = os.path.join(path, item)
            traverse_tracked_files(to_traverse, action_fn)
