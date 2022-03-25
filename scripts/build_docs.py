"""
Build the AgentOS documentation.

To use::

  $ python scripts/build_docs.py
"""
import argparse
import os
import pathlib
import shutil
from subprocess import Popen

from shared import docs_build_dir, docs_dir

import pcs

API_SOURCE_DIRS = ["agentos", "pcs"]
API_SOURCE_IGNORES = [
    "agentos/__init__.py",
    "agentos/cli.py",
    "pcs/__init__.py",
]
API_DOC_INCLUDES = "documentation/api_doc_includes"
API_DOC_TEMPLATE = "documentation/api_doc_templates/template.rst"
API_DOC_STUB_DIR = "documentation/api"
SOURCE_FILE_SUFFIX = ".py"

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
versioned_build_dir = os.path.join(docs_build_dir, f"{pcs.__version__}")


def update_latest_symlink():
    os.chdir(docs_build_dir)
    try:
        os.remove("latest")
    except FileNotFoundError:
        print("Latest symlink not found")

    try:
        os.symlink(pcs.__version__, "latest", target_is_directory=True)
    except OSError as e:
        print(
            "OSError: you might not have privileges to create symlink. "
            "Try running this script as Administrator."
        )
        raise e
    print(
        f"Created symbolic link {docs_build_dir}{os.sep}latest "
        f"pointing to {docs_build_dir}{os.sep}{pcs.__version__}"
    )


shutil.rmtree(API_DOC_STUB_DIR, ignore_errors=True)
for api_src_dir in API_SOURCE_DIRS:
    dest_dir = pathlib.Path(API_DOC_STUB_DIR) / api_src_dir
    print(f"Making dir {dest_dir}")
    dest_dir.mkdir(parents=True)
    assert pathlib.Path(dest_dir).is_dir()

# Copy over API doc includes
print(f"copying {API_DOC_INCLUDES} TO {API_DOC_STUB_DIR}")
shutil.copytree(API_DOC_INCLUDES, API_DOC_STUB_DIR, dirs_exist_ok=True)

# Generate API Doc stub files.
template = ""
with open(pathlib.Path(API_DOC_TEMPLATE), "r") as template_f:
    template = template_f.read()
for source_dir in API_SOURCE_DIRS:
    for source_name in pathlib.Path(source_dir).glob(f"*{SOURCE_FILE_SUFFIX}"):
        module_name = f"{source_dir}.{source_name.stem}"
        stub_filename = (
            pathlib.Path(API_DOC_STUB_DIR)
            / source_dir
            / (module_name + ".rst")
        )
        print(stub_filename)
        if f"{source_dir}/{source_name.name}" in API_SOURCE_IGNORES:
            print(f"ignoring {source_name}")
            continue
        with open(
            stub_filename,
            "w",
        ) as source_f:
            source_f.write(
                template.format(
                    module_name=module_name,
                    title=source_name.stem,
                    title_name_underline="=" * len(module_name),
                )
            )

if known_args.watch:
    build_tool = "sphinx-autobuild"
else:
    build_tool = "sphinx-build"
build_cmd = [build_tool, docs_dir, versioned_build_dir, "-c", docs_dir]
if known_args.release:
    build_cmd.append("-Dtodo_include_todos=0")
    update_latest_symlink()
for other_arg in unknown_args:
    build_cmd.append(other_arg)

print(f"Running command: {' '.join(build_cmd)}")
Popen(build_cmd).wait()
