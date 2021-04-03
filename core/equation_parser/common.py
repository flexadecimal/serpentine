# tunerpro math equation parser, used for converting to and from binary representations
import os
from pathlib import Path
from lark import (
  Lark,
  Tree
)
import pdb
# parse tree transformations 
from . import transformations
from .transformations import *
# transformation dict for neat semantics
transformations = {klass: getattr(getattr(transformations, klass), klass) for klass in transformations.__all__}

# TODO: move to INI config
grammar_name = 'tunerpro_math.lark'
schemata_path = os.path.abspath(os.path.join(Path(__file__).parent.parent, 'schemata'))
grammar_path = os.path.join(schemata_path, grammar_name)

# parse math
kwargs = dict(rel_to=__file__, start='statement')
parser = Lark.open(grammar_path, parser='lalr', **kwargs).parse

def expression_tree(equation):
  return parser(equation)