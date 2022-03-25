import os
from importlib.machinery import SourceFileLoader

from setuptools import find_packages, setup

version = (
    SourceFileLoader("pcs.version", os.path.join("pcs", "version.py"))
    .load_module()
    .VERSION
)

setup(
    name="agentos",
    description=(
        "AgentOS is a command line interface and python developer API "
        "for building, running, and sharing flexible learning agents."
    ),
    long_description=open("README.rst").read(),
    long_description_content_type="text/x-rst",
    author="Andy Konwinski",
    version=version,
    packages=find_packages(),
    install_requires=[
        "click>=7.0",
        "pyyaml>=5.4.1",
        "mlflow>=1.20.2",
        "dulwich==0.20.28",
        "requests>=2.21.0",
        "python-dotenv>=0.19.1",
        "rich>=10.15.2",
        "dill>=0.3.4",
    ],
    entry_points="""
        [console_scripts]
        agentos=agentos.cli:agentos_cmd
    """,
    license="Apache License 2.0",
    python_requires=">=3.5",
    keywords="reinforcement learning ai agent",
    url="https://agentos.org",
    project_urls={
        "Source Code": "https://github.com/agentos-project/agentos",
    },
)
