import os
from importlib.machinery import SourceFileLoader
from setuptools import setup, find_packages

version = SourceFileLoader(
    'agentos.version', os.path.join('agentos', 'version.py')).load_module().VERSION

setup(
    name='agentos',
    description='AgentOS is a command line interface and python developer API for building, running, and sharing flexible learning agents.',
    long_description=open("README.rst").read(),
    author='Andy Konwinski',
    version=version,
    packages=find_packages(),
    install_requires=[
        'click>=7.0',
        'mlflow==1.9.1',
        'gym==0.17.1',
        'numpy==1.19.3',
    ],
    entry_points='''
        [console_scripts]
        agentos=agentos.cli:agentos_cmd
    ''',
    license='Apache License 2.0',
    python_requires=">=3.5",
    keywords="reinforcement learning ai agent",
    url="https://agentos.org",
    project_urls={
        "Source Code": "https://github.com/agentos-project/agentos",
    },
)
