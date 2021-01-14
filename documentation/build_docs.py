"""
Build the AgentOS documentation.

To use::

  $ python documentation/build_docs.py
"""   

from importlib.machinery import SourceFileLoader
import os
import pip
from subprocess import Popen

docs_dir = os.path.dirname(os.path.abspath(__file__))

version = SourceFileLoader(
    'agentos.version', os.path.join(docs_dir, '..', 'agentos', 'version.py')).load_module().VERSION
Popen(["sphinx-build", docs_dir, f"{docs_dir}/../docs/{version}"]).wait()

os.chdir(f"{docs_dir}/../docs")
try:
    os.remove(f"latest")
except FileNotFoundError:
    print('Latest symlink not found')
os.symlink(version, "latest", target_is_directory=True)
print(f"Created symbolic link docs/latest pointing to docs/{version}")
