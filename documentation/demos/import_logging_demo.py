import builtins
import importlib
import pprint
import sys
from collections import defaultdict
from types import ModuleType
from graphviz import Digraph


class Graph:
    """Utility class."""
    def __init__(self):
        self.nodes = set()
        self.edges = defaultdict(set)


class ImportLogger:
    def __enter__(self):
        self.original_import = builtins.__import__
        builtins.__import__ = self._import_wrapper
        self.imports = {}
        return self

    def __exit__(self, *args):
        builtins.__import__ = self.original_import

    def log_import(
        self, name, imported, globals, locals=None, fromlist=(), level=0
    ):
        importer_name = globals["__name__"]
        im_file = imported.__file__ if hasattr(imported, '__file__') else ""
        self.imports[(importer_name, name)] = (imported, im_file)

    def _import_wrapper(self, name, *args, **kwargs):
        imported = self.original_import(name, *args, **kwargs)
        self.log_import(name, imported, *args, **kwargs)
        return imported


class Module:
    def __init__(self, name: str, version: str = None):
        self.name = name
        self._imports: [str, "Module"] = None

    @property
    def imports(self) -> [str, "Module"]:
        with ImportLogger() as importer:
            self.get()
            self._imports = importer.imports
        return self._imports

    def get(self) -> ModuleType:
        return importlib.import_module(self.name)

    def save_dag_file(self, filename):
        """Save a file representing the DAG associated with this Module."""
        gv_graph = Digraph(comment=f"Python module import DAG of {self.name}")
        g = self.generate_dag()  # get back a Graph object
        for node in g.nodes:
            gv_graph.node(node)  # Can specify 'shape=oval', etc.
        for parent, children in g.edges.items():
            for child in children:
                gv_graph.edge(parent, child)
        gv_graph.render(filename, view=True)
        print(f"Saved graph to {filename}")

    def generate_dag(self):
        """return a dot representation of the import DAG associated with this
        Module that will start at this Module and have edges to any Modules
        that it imports, and the modules they import, etc."""
        graph = Graph()
        for child, parent in self._imports.keys():
            graph.nodes.add(child)
            graph.nodes.add(parent)
            graph.edges[child].add(parent)
        return graph


if __name__ == "__main__":
    if len(sys.argv) > 1:
        module_name = sys.argv[1]
    else:
        print(f"sys.argv: {sys.argv}")
        exit("Please provide a package name as an arg to this script.")
    m = Module(module_name)
    pprint.pprint(m.imports)
    m.save_dag_file(f"{module_name}_import_dag.gv")
