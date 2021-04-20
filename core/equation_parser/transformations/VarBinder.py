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

#from .FunctionCallTransformer import FunctionCallTransformer

class VarBinder(Transformer):
  '''
  This transformation binds binary variables to other XDF items
  '''
  def __init__(self):
    super().__init__(visit_tokens=True)
    # we have function_registry already from parent
  
  def NAME(self, args):
    pdb.set_trace()
  
  def __default_token__(self, token):
    pdb.set_trace()
    pass