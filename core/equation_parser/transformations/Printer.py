from lark import (
  Lark,
  Tree
)
from lark.visitors import (
  v_args
)
from .TypeTransformer import TypeTransformer
import pdb

#from .FunctionCallTransformer import FunctionCallTransformer

class Printer(TypeTransformer):
  '''
  This transformation binds binary variables to other XDF items
  '''
  #def __init__(self):
  #  super().__init__(visit_tokens=True)
  
  # TODO - fix v_args not working here
  #@v_args(inline=True)
  def function(self, args):
    func, func_args = args
    return Tree(repr(func), func_args)
  
  #def str(self, tree):
  #  pdb.set_trace()
  #  pass
  
  def __default__(self, data, children, meta):
    return Tree(str(data), children, meta)