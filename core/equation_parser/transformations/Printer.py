import typing as T
from lark import Tree
from lark.visitors import v_args
from .TypeVisitors import TypeTransformer, func_printer

class Printer(TypeTransformer):
  '''
  This transformation is used in printing ASTs internally by converting values of other types to their string representations.
  '''
  #def __init__(self):
  #  super().__init__(visit_tokens=True)
  
  # TODO - fix v_args not working here
  #@v_args(inline=True)
  def function(self, args: T.List):
    func: T.Callable = args[0]
    func_args: T.List = args[1]
    return Tree(f"<function '{func_printer(func)}'>", func_args)
  
  #def str(self, tree):
  #  pass
  
  def __default__(self, data, children, meta):
    return Tree(str(data), children, meta)