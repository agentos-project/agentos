"""
Build the AgentOS documentation.

To use::

  $ python scripts/build_docs.py
"""
import argparse
import os
from subprocess import Popen

import agentos
from shared import docs_dir
from shared import docs_build_dir

parser = argparse.ArgumentParser(
    description="Build the AgentOS docs. Any arguments that are provided "
    "that do not match those listed below will be passed through "
    "as arguments to the `sphinx-build` command, which is used "
    "under the hood to build the docs (or the `sphinx-autobuild` command, "
    "which is used under the hood if the `--watch` flag is passed)."
)
parser.add_argument(
    "--release",
    action="store_true",
    help="Build docs for release. This causes TODO directives to be ignored "
    "so that they are not shown in the documentation generated. It also "
    "causes the `latest` symlink to get updated (or generated) to point "
    "to the docs that are built.",
)
parser.add_argument(
    "--watch",
    action="store_true",
    help="Use sphinx-autobuild instead of sphinx-build under the hood to "
    "start a web server and watch for changes to the documentation, "
    "and automatically rebuild the docs.",
)
known_args, unknown_args = parser.parse_known_args()
versioned_build_dir = os.path.join(docs_build_dir, f"{agentos.__version__}")


def update_latest_symlink():
    os.chdir(docs_build_dir)
    try:
        os.remove("latest")
    except FileNotFoundError:
        print("Latest symlink not found")

    try:
        os.symlink(agentos.__version__, "latest", target_is_directory=True)
    except OSError as e:
        print(
            "OSError: you might not have privileges to create symlink. "
            "Try running this script as Administrator."
        )
        raise e
    print(
        f"Created symbolic link {docs_build_dir}{os.sep}latest "
        f"pointing to {docs_build_dir}{os.sep}{agentos.__version__}"
    )


if known_args.watch:
    build_tool = "sphinx-autobuild"
else:
    build_tool = "sphinx-build"
build_cmd = [build_tool, docs_dir, versioned_build_dir, "-c", "documentation"]
if known_args.release:
    build_cmd.append("-Dtodo_include_todos=0")
    update_latest_symlink()
for other_arg in unknown_args:
    build_cmd.append(other_arg)
Popen(build_cmd).wait()
