from __future__ import annotations
# tunerpro math equation parser, used for converting to and from binary representations
from typing import *
import os
from pathlib import Path
from lark import Lark, Tree, Transformer
# for printing
from .transformations.Printer import Printer
from functools import reduce
from operator import mul

# TODO: move to INI config
grammar_name = 'tunerpro_math.lark'
schemata_path = os.path.abspath(os.path.join(Path(__file__).parent.parent, 'schemata'))
grammar_path = os.path.join(schemata_path, grammar_name)

# parse math
kwargs = dict(rel_to=__file__, start='statement')
parser = Lark.open(grammar_path, parser='lalr', **kwargs).parse

# shadow __repr__ so i can debug this thing
def ast_print(tree: Tree) -> str:
  printer = Printer(visit_tokens = True)
  stringified = printer.transform(tree)
  return stringified.pretty()

class SyntaxTree(Tree):
  def __init__(self):
    Tree.__init__(self)
  
  def __repr__(self):
    return ast_print(self)

# TODO: typehint generic tree for lark?
def apply_pipeline(source: Tree, *transformation_instances: Transformer):
  # chaining transformations, see:
  # https://lark-parser.readthedocs.io/en/latest/visitors.html#visitor
  combined: Transformer = reduce(mul, transformation_instances)
  out: SyntaxTree = combined.transform(source)
  out.__class__ = SyntaxTree
  return out
