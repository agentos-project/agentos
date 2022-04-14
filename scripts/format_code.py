"""
Run black code formatter on AgentOS Python files

To use::

  # Format all code
  $ python scripts/format_code.py

  # Format specific files
  $ python scripts/format_code.py [path/to/file1] [path/to/file2]

  # Print files that will be formatted, but don't actually format
  $ python scripts/format_code.py --check
"""

import os
import sys
from pathlib import Path
from subprocess import PIPE, STDOUT, run

from shared import root_dir, traverse_tracked_files

returncode = 0

IGNORED_FILES = [
    "agentos/templates/agent.py",
]

CHECK_ARG = "--check"


def format_file(path):
    # Run codespell on every tracked file
    codespell_cmd = ["codespell", path, "-w"]
    if CHECK_ARG in sys.argv:
        codespell_cmd.remove("-w")
    _run_command(path, codespell_cmd)

    # black, isort, and pyupgrade only run on Python
    extension = os.path.splitext(path)[1]
    if extension != ".py":
        return

    # black to format code
    black_cmd = ["black", "--line-length=79", path]
    if CHECK_ARG in sys.argv:
        black_cmd.append("--check")
    _run_command(path, black_cmd)

    # isort to arrange import statements:w
    isort_cmd = ["isort", "-m" "VERTICAL_HANGING_INDENT", "--tc", path]
    if CHECK_ARG in sys.argv:
        isort_cmd.append("--check")
    _run_command(path, isort_cmd)

    # pyupgrade to upgrade deprecated lines
    pyupgrade_cmd = ["pyupgrade", "--py37-plus", path]
    _run_command(path, pyupgrade_cmd)


def _run_command(path, cmd):
    global returncode
    result = run(cmd, stdout=PIPE, stderr=STDOUT)
    returncode = returncode | result.returncode
    out = result.stdout.decode("utf-8")
    if out:
        print(path)
        print(out)
        print()


check_count = 1 if CHECK_ARG in sys.argv else 0

if len(sys.argv) - check_count > 1:
    for arg in sys.argv[1:]:
        if arg == "--check":
            continue
        path = Path(arg).absolute()
        format_file(path)
else:
    traverse_tracked_files(root_dir, format_file, IGNORED_FILES)
sys.exit(returncode)
