from setuptools import setup

setup(
    name="setup_py_agent",
    description=(
        "An agent with requirements in setup.py for AOS testing purposes"
    ),
    version="1.0.0",
    install_requires=[
        "arrow",
        "bottle",
    ],
    license="Apache License 2.0",
    python_requires=">=3.5",
    url="https://agentos.org",
    project_urls={
        "Source Code": "https://github.com/agentos-project/agentos",
    },
)
