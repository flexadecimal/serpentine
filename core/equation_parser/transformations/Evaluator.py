
from . import GenericTree
import typing as t
from .Replacer import NumericFunctionTreeNode
from .TypeVisitors import TypeTransformer
from .FunctionCallTransformer import NumericArg, ConversionFunc
import numpy.typing as npt

# function composition, see:
# https://stackoverflow.com/questions/16739290/composing-functions-in-python/16739663#16739663
#def compose(*funcs: List[Callable[[float], Callable]]) -> Callable:
#  # original does a, b, c = c(b(a(x))), we do it reversed a, b, c = a(b(c(x)))
#  ordered = reversed(funcs)
#  def composed(x):
#    return functools.reduce(lambda acc, f: f(acc), ordered, x)
#  # set docstring to nested representation e.g. 'f(g(h(x)))'
#  nested_call_str = functools.reduce(
#    lambda prev, func: f'{func_printer(func)}({prev})',
 #   ordered, 
 #   # initial args
 #   '*args'
 # )
 # # set doc to dev-friendly composition expression
 # composed.__name__ = nested_call_str
 # return composed
class Evaluator(TypeTransformer[NumericFunctionTreeNode, npt.ArrayLike]):
  '''
  Intended to be called after `FunctionCallTransformer`, which will have rendered
  a tree like:
  "0.007813*X + Y + 2 + L" ->
  ```
  statement
    <function sum at 0x7f54991c1e50>
      <ufunc 'multiply'>
        X
        0.007813
      Y
      2
      L
  ```
  Free variables and duplicates like Y or L = X will have been replaced using 
  the `Replacer` transformation.
  
  TODO:
  This could stand to be refactored in a more functional style by replacing
  vars with literals and combining using function composition and 
  functools.partial, or a more general combinator pattern. Currently, the AST must be walked for each calculation.
  '''
  def __init__(self, visit_tokens: bool = True) -> None:
    super().__init__(visit_tokens)

  # this 'function` dispatch is magic from `TypeVisitors`
  def function(self, args):
    func: ConversionFunc = args[0]
    func_args: t.List[NumericArg] = args[1]
    # KISS - everything shouldve been replaced by now
    return func(*func_args)
  
  def __default__(self, data, children, meta):
    return GenericTree(data, children, meta)