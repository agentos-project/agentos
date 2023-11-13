import infer  # noqa: F401 isort: skip
import arrow  # ==1.1.1
import numpy  # ==1.22.4
import regex

# NB - latest version of numpy is 1.23.2
print(
    f"Numpy version is {numpy.__version__} "
    '(should be "1.22.4", NOT latest version "1.23.2")'
)
assert numpy.__version__ == "1.22.4"

# NB - latest version of arrow is 1.2.2
print(
    f"Arrow version is {arrow.__version__} "
    '(should be "1.1.1", NOT latest version "1.2.2")'
)
assert arrow.__version__ == "1.1.1"

# NB - latest version of regex is 2.5.119
print(
    f"Regex version is {regex.__version__} "
    '(should be latest version "2.5.119")'
)
assert regex.__version__ == "2.5.119"
