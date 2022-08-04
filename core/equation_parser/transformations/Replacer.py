from .GenericTree import GenericTree
import typing as t
import numpy.typing as npt
import lark
from .TypeVisitors import TypeTransformer
from .FunctionCallTransformer import (
  ConversionFunc,
  NumericArg,
  FunctionTree,
  FunctionTreeNode
)

NumericLeaf = t.Union[NumericArg, ConversionFunc]
NumericFunctionTree = GenericTree[ConversionFunc, NumericLeaf]
NumericFunctionTreeNode = NumericLeaf | NumericFunctionTree

class Replacer(TypeTransformer[FunctionTree, NumericFunctionTree]):
  '''
  Replaces things using a dictionary specification, provided as a dict or as
  keyword arguments. Each source key will be replaced with the value element.
  Elements not specified will be preserved.
  '''
  def __init__(self, replacement_spec: t.Mapping[str, npt.ArrayLike]):
    super().__init__(visit_tokens = True)
    self.replacement_spec = replacement_spec
  
  def NAME(self, token: lark.Token):
    name = token[0]
    if name in self.replacement_spec.keys():
      return self.replacement_spec[name]
    else:
      return token

  def __default__(self, data, children, meta):
    return NumericFunctionTree(data, children, meta)
