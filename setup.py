import os
from importlib.machinery import SourceFileLoader
from setuptools import setup, find_packages

version = SourceFileLoader(
    'agentos.version', os.path.join('agentos', 'version.py')).load_module().VERSION

setup(
    name='agentos',
    author='Andy Konwinski',
    version=version,
    packages=find_packages(),
    install_requires=[
        'click>=7.0',
        'Flask>=1.1.2',
        'mlflow',
        'pyyaml',
        'ray',
        'requests>=2.17.3',
        'waitress',
    ],
    entry_points='''
        [console_scripts]
        agentos=agentos.cli:agentos_cmd
    ''',
    license='Apache License 2.0',
)
