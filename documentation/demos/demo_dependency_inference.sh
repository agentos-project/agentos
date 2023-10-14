#!/bin/bash
set -xe

pip install pcs
pcs activate
# Create an empty VirtualEnv; point 'base' alias at it; activate it.
python --version
# 3.9.10
python -c "import numpy; print(numpy.random)"
# Create a new VirtualEnv; pip install numpy into it; run this command in it.
# stdout: 28.37  <--some random number

pcs list --type Command
# Identifier    Type      Aliases
# 3857a         Command   last, 0

pcs list
# Identifier    Type          Aliases
# 3857a         Command       last_Command, 0
# 7b6c0         VirtualEnv    last_VirtualEnv
# 45abd         VirtualEnv    base

pcs config set default-py 3.8.3  # updates ~/.pcsconfig.yaml
# Create new empty VirtualEnv with Python 3.8.3; point alias 'base' at it
python --version  # Creates a new VirtualEnv with Python 3.8.3
# 3.8.3

virtualenv my_new_venv  # creates a new alias in the local_registry pointing
                        # to the venv Component that is was currently in-use.
ls
# my_new_venv <-- this is a symlink to the venv in the ~/.pcs/cache/ dir
# other_files_and_folders

pcs list --type VirtualEnv
