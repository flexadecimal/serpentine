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

class XDFAxisFunctor(Transformer):
  '''
  Syntax tree transformation that binds the following XDF Axis specific functions:
  - INDEX()
  - INDEXES()
  - CELL(index; precalc)
  
  See `GenConv.htm` original TunerPro documentation for info on these functions.
  '''
  
  def index(x):
    return np.arange(len(x))
  
  def indexes(x):
    return len(x)
    
  def cell(x, index, precalc):
    return x[index]
  
  function_registry = {
    'INDEX': index,
    'INDEXES': indexes,
    'CELL:': cell
  }
  
  def __init__(self):
    super().__init__(visit_tokens=True)
    # we have function_registry already from parent
    
  def __default_token__(self, token):
    pdb.set_trace()
    pass