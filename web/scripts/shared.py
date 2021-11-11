"""
Lints AgentOS Python files

To use::

  $ python scripts/lint_code.py
"""

import os
from subprocess import run
from subprocess import DEVNULL

scripts_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.normpath(os.path.join(scripts_dir, os.pardir))
docs_dir = os.path.join(root_dir, "documentation")
docs_build_dir = os.path.join(root_dir, "docs")


def is_git_tracked(file_path):
    cmd = ["git", "ls-files", "--error-unmatch", file_path]
    result = run(cmd, stdout=DEVNULL, stderr=DEVNULL)
    return result.returncode == 0


def traverse_tracked_files(path, action_fn, ignored_files=None):
    if not is_git_tracked(path):
        return

    if ignored_files:
        for relative_path in ignored_files:
            ignored_path = os.path.join(root_dir, relative_path)
            error = f"Ignored file {ignored_path} does not exist"
            assert os.path.isfile(ignored_path), error
            if path == ignored_path:
                return

    if os.path.isfile(path):
        action_fn(path)

    if os.path.isdir(path):
        for item in os.listdir(path):
            to_traverse = os.path.join(path, item)
            traverse_tracked_files(to_traverse, action_fn, ignored_files)
