from lark import (
  Lark,
  Tree
)
from lark.visitors import (
  Transformer,
  v_args
)
import numpy as np
import pdb

from .FunctionCallTransformer import FunctionCallTransformer

class Inverter(FunctionCallTransformer):
  '''
  Where the Numpifier is used to get a call tree for binary-to-measure conversion,
  e.g. binary-parsed [20, 22, 24] -> x*30 -> [600, 660, 720] RPM,
  the inverter is used to save tp the binary file, e.g.
  [600, 660, 720] RPM -> x/30 -> [20, 22, 24].
  '''
  def __init__(self):
    super().__init__(visit_tokens=True)
    # we have function_registry already from parent
    
  def __default_token__(self, token):
    pdb.set_trace()
    pass