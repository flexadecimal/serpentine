import typing as T
from lark import (
  Lark,
  Tree
)
from lark.lexer import Token
from lark.visitors import (
  v_args
)
from .TypeVisitors import TypeTransformer

class Replacer(TypeTransformer):
  '''
  Replaces things using a dictionary specification, provided as a dict or as
  keyword arguments. Each source key will be replaced with the value element.
  Elements not specified will be preserved.
  '''
  def __init__(self, replacement_spec: T.Dict[str, T.Any]):
    super().__init__(visit_tokens = True)
    self.replacement_spec = replacement_spec
  
  def NAME(self, token):
    name = token[0]
    if name in self.replacement_spec.keys():
      return self.replacement_spec[name]
    else:
      return token