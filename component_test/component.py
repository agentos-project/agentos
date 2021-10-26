import importlib
import sys


def load_component(file_path, class_name, python_path):
    old_sys_module_keys = [k for k in sys.modules.keys()]
    old_sys_path = sys.path
    sys.path = [python_path, "."]
    spec = importlib.util.spec_from_file_location(
        "TEMP_MODULE", str(file_path)
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    cls = getattr(module, class_name)
    sys.path = old_sys_path
    # Invalidate any new keys added to modules via secondary imports in module
    for key in [k for k in sys.modules.keys()]:
        if key not in old_sys_module_keys:
            del sys.modules[key]
    return cls()


baz_a = load_component("baz.py", "Baz", "a/")
baz_b = load_component("baz.py", "Baz", "b/")

print("Should be AAAAAA:")
baz_a.test()
print()

print("Should be BBBBBB:")
baz_b.test()
print()

print("Should be AAAAAA:")
baz_a.test()
print()

print("Should be BBBBBB:")
baz_b.test()
