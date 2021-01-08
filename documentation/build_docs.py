"""
Build the AgentOS documentation.

To use::

  $ cd documentation
  $ pip install -r requirements.txt
  $ python build_docs
"""   

import os
from importlib.machinery import SourceFileLoader
from subprocess import Popen

version = SourceFileLoader(
    'agentos.version', os.path.join('..', 'agentos', 'version.py')).load_module().VERSION

Popen(["sphinx-build", ".", f"../docs/{version}"])
print(f"docs built in <project_root>/docs/{version}")
