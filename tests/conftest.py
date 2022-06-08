import functools
import sys

import pytest
from click.testing import CliRunner


# From https://github.com/pallets/click/issues/737#issuecomment-309231467
# We use this to capture the stdout of Click's CliRunner.
@pytest.fixture
def cli_runner():
    """Yield a click.testing.CliRunner to invoke the CLI."""
    class_ = CliRunner

    def invoke_wrapper(f):
        """Augment CliRunner.invoke to emit its output to stdout.

        This enables pytest to show the output in its logs on test
        failures.

        """

        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            echo = kwargs.pop("echo", False)
            result = f(*args, **kwargs)

            if echo is True:
                sys.stdout.write(result.output)

            return result

        return wrapper

    class_.invoke = invoke_wrapper(class_.invoke)
    cli_runner = class_()

    yield cli_runner


def test_basic(cli_runner, package):
    result = cli_runner.invoke(package, ["--help"])
    assert result.exit_code == 0
