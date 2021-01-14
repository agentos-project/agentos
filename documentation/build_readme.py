"""
This script builds the main AgentOS project readme, using
source from the documentation so that there is no duplication
of efforts and fewer chances for bugs.

To use::

  python documentation/build_readme.md
"""

import os

docs_dir = os.path.dirname(os.path.abspath(__file__))
target_readme = f"{docs_dir}/../README.rst"

with open(target_readme, "w") as readme_f:
    def include(src_file):
        with open(src_file, "r") as f:
            readme_f.write(f.read())


    include(docs_dir + '/includes/intro.rst')
    readme_f.write("\n\nThe AgentOS docs are at `agentos.org "
                   "<https://agentos.org>`_.\n\n\n")

    include(docs_dir + '/includes/install_and_try.rst')
    readme_f.write("\n\n")

    include(docs_dir + '/includes/developing.rst')
    readme_f.write("\n\n")

    readme_f.write("----\n\n" +
                   "*This README was compiled from the project " +
                   "documentation by running:\n" +
                   f"``python documentation/{os.path.basename(__file__)}``.*")
