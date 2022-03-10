"""
Run mypy static type checker on code in repo.

To use::

  $ python scripts/typecheck_code.py
"""

import sys
from subprocess import run, PIPE, STDOUT

returncode = 0

cmd = ["mypy", "agentos", "--exclude", "agentos/templates"]
print(f"running {' '.join(cmd)}")
result = run(cmd, stdout=PIPE, stderr=STDOUT)
out = result.stdout.decode("utf-8")
returncode = returncode | result.returncode
if out:
    print(out)
    print()

sys.exit(returncode)
