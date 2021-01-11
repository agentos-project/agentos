"""
Build the AgentOS documentation.

To use::

  $ cd documentation
  $ pip install -r requirements.txt
  $ python build_docs.py
"""   

import os
from importlib.machinery import SourceFileLoader
from subprocess import Popen

docs_dir = os.path.dirname(os.path.abspath(__file__))
version = SourceFileLoader(
    'agentos.version', os.path.join(docs_dir, '..', 'agentos', 'version.py')).load_module().VERSION
Popen(["sphinx-build", docs_dir, f"{docs_dir}/../docs/{version}"]).wait()
