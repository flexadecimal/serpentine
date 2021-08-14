# tunerpro math equation parser, used for converting to and from binary representations
import os
from pathlib import Path
from lark import Lark
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

def ast_print(tree):
  printer = Printer(visit_tokens = True)
  stringified = printer.transform(tree)
  return stringified.pretty()
  
def apply_pipeline(source, *transformation_instances):
  # chaining transformations, see:
  # https://lark-parser.readthedocs.io/en/latest/visitors.html#visitor
  combined = reduce(mul, transformation_instances)
  return combined.transform(source)
