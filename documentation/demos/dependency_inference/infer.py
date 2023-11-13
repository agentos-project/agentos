import builtins
import inspect
import subprocess
import sys
import tokenize
from pathlib import Path

if __name__ == "__main__":
    print("Infer library: import into your code, do not run directly")
    sys.exit(0)


# Let's find the file importing us
# https://docs.python.org/3/library/inspect.html#the-interpreter-stack
def get_importing_file():
    IGNORED_FILES = [
        "<frozen importlib._bootstrap_external>",
        "<frozen importlib._bootstrap>",
    ]
    curr_frame = inspect.currentframe()
    try:
        outer = inspect.getouterframes(curr_frame)
        for frame in outer:
            if frame.filename == __file__:
                continue
            # consider using code_context here?
            if frame.filename not in IGNORED_FILES:
                break
        else:
            raise Exception("No import site found")
        target_file = Path(frame.filename)
    finally:
        del frame
    return target_file


# Return a map from {lineno -> comment} for all import statements found
def get_comment_map(target_file):
    comment_map = {}
    with open(target_file, "rb") as fin:
        in_import = False
        for token in tokenize.tokenize(fin.readline):
            if token.type == tokenize.NAME and token.string == "import":
                in_import = True
                continue
            if token.type == tokenize.NEWLINE:
                in_import = False
            if token.type == tokenize.COMMENT and in_import:
                comment_map[token.start[0]] = token.string.strip("#").strip()
    return comment_map


importing_file = get_importing_file()
comment_map = get_comment_map(importing_file)

print(f"Infer library imported by: {importing_file}")
print(f"Infer library found the following comments: {comment_map}")

original_import = builtins.__import__


def handle_user_relevant_import(name, version_modifier):
    p = subprocess.run(
        [sys.executable, "-m", "pip", "show", f"{name}"], capture_output=True
    )
    installed_version = ""
    for line in p.stdout.decode().split("\n"):
        if line.startswith("Version: "):
            installed_version = line[9:].strip()
    # TODO - gross string ops here, comment_version_modifier is '==1.2.1'
    #        if we have wrong version or no version, install package
    if version_modifier[2:] != installed_version or installed_version == "":
        cmd = [
            str(sys.executable),
            "-m",
            "pip",
            "install",
            f"{name}{version_modifier}",
        ]
        subprocess.run(cmd, check=True)


def new_import(name, globals=None, locals=None, fromlist=(), level=0):
    curr_frame = inspect.currentframe()
    outer = inspect.getframeinfo(curr_frame.f_back)
    if outer.filename == str(importing_file):
        print(f"Infer library detected an import={name}")
        handle_user_relevant_import(name, comment_map.get(outer.lineno, ""))
        module = original_import(
            name,
            globals=globals,
            locals=locals,
            fromlist=fromlist,
            level=level,
        )
    else:
        module = original_import(
            name,
            globals=globals,
            locals=locals,
            fromlist=fromlist,
            level=level,
        )
    return module


builtins.__import__ = new_import


# Based on
# https://realpython.com/python-import/#example-automatically-install-from-pypi
# class TestMeta:
#     @classmethod
#     def find_spec(cls, name, path, target=None):
#         global activate_test_meta
#         global comment_version_modifier
#         if not activate_test_meta:
#             return
#         # print(f"TestMeta: name={name}, path={path}, target={target}:")
#         module_found = False
#         for meta in sys.meta_path:
#             if meta is cls:
#                 continue
#             module_spec = meta.find_spec(name, path, target)
#             # print(f"\t META_SEARCH {meta} -> {module_spec}")
#             if module_spec is not None:
#                 module_found = True
#         if not module_found:
#             cmd = [
#                 str(sys.executable),
#                 "-m",
#                 "pip",
#                 "install",
#                 f"{name}{comment_version_modifier}",
#             ]
#             try:
#                 subprocess.run(cmd, check=True)
#             except subprocess.CalledProcessError:
#                 return None
#         elif comment_version_modifier:
#             p = subprocess.run(
#               [sys.executable, '-m', 'pip', 'show', f'{name}'],
#               capture_output=True,
#             )
#             for line in p.stdout.decode().split('\n'):
#                 if line.startswith('Version: '):
#                     installed_version = line[9:].strip()
#             # TODO - gross string ops here
#             if comment_version_modifier[2:] != installed_version:
#                 print(f'BAD INSTALL {name}')
#                 print(comment_version_modifier)
#                 print(installed_version)
#                 print()
#         activate_test_meta = False


# sys.meta_path.insert(0, TestMeta)

# TODO:
#   * If installed version is as requested, and reinstall if not
#   * Rewrite file with version annotations
#   * Cleanup
#   * Summarize findings and intermediate PR
#   * Multi-file systems

# Thoughts: some imports the user cares about, internal package imports they
# probably don't.  Can we distinguish between packages users care about and
# those that they don't?  Do we have to if we only install if package is
# missing (seems like numpy internally uses ModuleNotFound)


# //NEXT :  PIPFINDER gets the comment map and the metafinder will try to
# install //specified versions (probably use frame inspection to figure out
# lineno)

# //the trick will be to distinguish imports the user cares about (i.e. in
# their //packages) vs imports the user doesn't care about (imports internal to
# numpy)
