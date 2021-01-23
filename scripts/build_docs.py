"""
Build the AgentOS documentation.

To use::

  $ python scripts/build_docs.py
"""
import os
from subprocess import Popen

import agentos
from shared import docs_dir
from shared import docs_build_dir

versioned_build_dir = os.path.join(docs_build_dir, f"{agentos.__version__}")

Popen(["sphinx-build", docs_dir, versioned_build_dir]).wait()

os.chdir(docs_build_dir)

try:
    os.remove("latest")
except FileNotFoundError:
    print("Latest symlink not found")

os.symlink(agentos.__version__, "latest", target_is_directory=True)
print(
    f"Created symbolic link {docs_build_dir}{os.sep}latest "
    f"pointing to {docs_build_dir}{os.sep}{agentos.__version__}"
)
