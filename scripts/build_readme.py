"""
This script builds the main AgentOS project readme, using
source from the documentation so that there is no duplication
of efforts and fewer chances for bugs.

To use::

  python scripts/build_readme.py
"""

import os

from shared import docs_dir

DOC_SECTIONS_PLUS_SEPARATOR_TEXT = [
    (
        "intro.rst",
        "\n\nQuickstart\n===========\n\n"
        "See the agentos.org `quickstarts "
        "<https://agentos.org/latest/quickstart>`_.\n\n\n"
        "\n\nDocumentation\n=============\n\n"
        "For detailed documentation see the "
        "`agentos.org docs <https://agentos.org/latest>`_.\n\n\n",
    ),
    ("developing.rst", "\n\n"),
]

target_readme = os.path.join(docs_dir, os.pardir, "README.rst")

with open(target_readme, "w") as readme_f:

    def include_docs_section(src_filename, separator_text):
        text_path = os.path.join(docs_dir, "includes", src_filename)
        with open(text_path) as f:
            readme_f.write(f.read())
            readme_f.write(separator_text)

    for section_info, sep_text in DOC_SECTIONS_PLUS_SEPARATOR_TEXT:
        include_docs_section(section_info, sep_text)

    readme_f.write(
        "----\n\n"
        "*This README was compiled from the project "
        "documentation via:*\n``python "
        f"scripts/{os.path.basename(__file__)}``."
    )
