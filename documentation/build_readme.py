"""
This script builds the main AgentOS project readme, using
source from the documentation so that there is no duplication
of efforts and fewer chances for bugs.

To use::

  python documentation/build_readme.py
"""

import os

docs_dir = os.path.dirname(os.path.abspath(__file__))
target_readme = os.path.join(docs_dir, os.pardir, 'README.rst')

with open(target_readme, "w") as readme_f:
    def include(src_file):
        with open(src_file, "r") as f:
            readme_f.write(f.read())
    
    intro_text = os.path.join(docs_dir, 'includes', 'intro.rst')
    include(intro_text)
    readme_f.write("\n\nThe AgentOS docs are at `agentos.org "
                   "<https://agentos.org>`_.\n\n\n")

    install_text = os.path.join(docs_dir, 'includes', 'install_and_try.rst')
    include(install_text)
    readme_f.write("\n\n")

    developing_text = os.path.join(docs_dir, 'includes', 'developing.rst')
    include(developing_text)
    readme_f.write("\n\n")

    readme_f.write("----\n\n"
                   "*This README was compiled from the project "
                   "documentation via:*\n``python "
                   f"documentation{os.sep}{os.path.basename(__file__)}``.")
