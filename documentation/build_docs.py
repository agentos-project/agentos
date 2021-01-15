"""
Build the AgentOS documentation.

To use::

  $ python documentation/build_docs.py
"""   

from importlib.machinery import SourceFileLoader
import os
from subprocess import Popen

docs_dir = os.path.dirname(os.path.abspath(__file__))
version_file = os.path.join(docs_dir, os.pardir, 'agentos', 'version.py')
loaded = SourceFileLoader('agentos.version', version_file).load_module()
version = loaded.VERSION

build_dir = os.path.normpath(os.path.join(docs_dir, os.pardir, "docs"))
versioned_build_dir = os.path.join(build_dir, f"{version}")

Popen(["sphinx-build", docs_dir, versioned_build_dir]).wait()

os.chdir(build_dir)

try:
    os.remove(f"latest")
except FileNotFoundError:
    print('Latest symlink not found')

os.symlink(version, "latest", target_is_directory=True)
print(f"Created symbolic link {build_dir}{os.sep}latest "
      f"pointing to {build_dir}{os.sep}{version}")
