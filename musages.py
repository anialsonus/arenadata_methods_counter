"""Main module"""

import argparse
import ast
import csv
import os
import pprint
from dataclasses import dataclass
from pathlib import Path
from typing import Counter, List, Mapping, Optional, Sequence


@dataclass
class Import:
    """Helper class for organising tracking methods usage"""

    module: str
    name: str
    asname: Optional[str] = None

    @property
    def id(self) -> str:
        """String used to access an object within the given file"""

        return self.asname or self.name

    @property
    def key(self) -> str:
        """Import value key independent from the alias given to the imported object"""

        return f"{self.module}.{self.name}"


class ImportCollector(ast.NodeVisitor):
    """NodeVisitor aimed for collecting ImportFrom statements in the code"""

    def __init__(self, name: str, acc: List[Import]) -> None:
        super().__init__()
        self.name = name
        self.acc = acc

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module and node.module.startswith(self.name):
            self.acc.extend(Import(node.module, alias.name, alias.asname) for alias in node.names)
        self.generic_visit(node)


class CallsCollector(ast.NodeVisitor):
    """NodeVisitor aimed for collecting Call statements in the code"""

    def __init__(self, ids: Mapping[str, str], hits) -> None:
        super().__init__()
        self.ids = ids
        self.hits = hits

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name) and node.func.id in self.ids:
            self.hits.append(self.ids[node.func.id])
        self.generic_visit(node)


def parse_file(path: Path) -> ast.AST:
    """Parse the given file to AST"""

    with open(path, "r", encoding="utf-8") as file:
        data = file.read()
    return ast.parse(data, path.name)


def get_calls(root: Path, module: str) -> List[str]:
    """Collect module's calls"""

    hits: List[str] = []

    for path in root.glob("**/*.py"):
        tree = parse_file(path)
        imports: List[Import] = []
        ImportCollector(module, imports).visit(tree)
        mapping = {i.id: i.key for i in imports}
        CallsCollector(mapping, hits).visit(tree)

    return hits


def main(argv: Optional[Sequence[str]] = None) -> None:
    """Application entry point"""

    parser = argparse.ArgumentParser()
    parser.add_argument("sources", help="path to directory to observe python files", type=Path)
    parser.add_argument("-m", help="module name for collecting methods", required=True)
    parser.add_argument("-o", help="file name to print output stats")
    args = parser.parse_args(argv)

    # The only reasonable check at the moment
    if not os.path.isdir(args.sources):
        raise SystemExit("given path is not a directory")

    hits = Counter(get_calls(args.sources, args.m))

    if args.o:
        with open(args.o, "w", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerows(hits.most_common())
            return

    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(hits)
