# tunerpro math equation parser, used for converting to and from binary representations
import typing as t
import os
from pathlib import Path
import lark
# for printing
from functools import reduce
from operator import mul

# TODO: move to INI config
grammar_name = 'tunerpro_math.lark'
schemata_path = os.path.abspath(os.path.join(Path(__file__).parent.parent, 'schemata'))
grammar_path = os.path.join(schemata_path, grammar_name)

# parse math
kwargs = dict(rel_to=__file__, start='statement')
parser = lark.Lark.open(grammar_path, parser='lalr', **kwargs).parse

TransformLeaf = t.TypeVar('TransformLeaf')
TransformReturn = t.TypeVar('TransformReturn')
def apply_pipeline(
  source: lark.Tree, 
  *transformations: lark.Transformer,
) -> TransformReturn:
  # chaining transformations, see:
  # https://lark-parser.readthedocs.io/en/latest/visitors.html#visitor
  combined: lark.Transformer = reduce(mul, transformations)
  out = combined.transform(source)
  return out
