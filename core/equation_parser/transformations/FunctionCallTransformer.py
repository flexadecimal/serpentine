from .GenericTree import GenericTree
import typing as t
import lark
from lark.visitors import (
  Transformer,
  v_args
)
import numpy as np
import numpy.typing as npt
import functools
from collections import deque

NumericArg = npt.ArrayLike
EquationArg = NumericArg | lark.Token
ConversionFunc = t.Callable[..., NumericArg]
EquationLeaf = t.Union[ConversionFunc, EquationArg]
# intermediate transformer tree has "statement" data, string invariant
FunctionParseTree = lark.Tree[EquationLeaf]
# output tree has no "statement"
FunctionTree = GenericTree[ConversionFunc, EquationArg]
# generic data or leaf type
FunctionTreeNode = EquationLeaf | lark.ParseTree | FunctionTree

def if_func(condition: bool, true_val: EquationArg, false_val: EquationArg) -> EquationArg:
  return true_val if condition else false_val

# so we dont have to do fancy type dispatch on args, a version of sum that
# takes variable arguments
def sum_args(*args) -> npt.ArrayLike:
  return functools.reduce(np.add, args)

# these shadows of bitwise operations can raise optionally raise rounding error,
# for super-strict mode
class RoundingError(ValueError):
  pass

def int_or_raise(n: NumericArg):
  as_array = np.array(n)
  # see https://stackoverflow.com/a/7236784
  is_int = np.all(np.equal(np.mod(as_array, 1), 0))
  #if not is_int:
  #  raise RoundingError("WARNING: Float values being truncated for bitwise operation.")
  return as_array.astype(np.integer)

def int_truncate(*ns: NumericArg):
  return map(int_or_raise, ns)

def int_truncated(bitwise: np.ufunc | t.Callable[[NumericArg, NumericArg], npt.NDArray]):
  def inner(a: NumericArg, b: NumericArg) -> npt.NDArray:
    a, b = int_truncate(a, b)
    return bitwise(a, b)
  return inner

class FunctionCallTransformer(Transformer[lark.Token, FunctionTree]):
  '''
  Transforms an equation AST (abstract syntax tree) to one with vectorized numpy functions. This is an intermediate syntactical form - the arguments must still processed as functions by calling along the tree.
  '''
  # DISPATCH TABLE
  function_registry: t.Dict[str, ConversionFunc] = {
    # MATH FUNCTIONS
    'ABS': np.abs,
    'AVG': np.average,
    'EXP': np.exp,
    'LOG': np.log,
    'POW': np.float_power,
    'SQR': np.sqrt,
    'SUM': sum_args,
    'LOG10': np.log10,
    'RADIANS': np.radians,
    'DEGREES': np.degrees,
    'IF': if_func,
    'ROUND': round,
    'MROUND': np.floor_divide,
    'SIN': np.sin,
    'COS': np.cos,
    'TAN': np.tan,
    'SINH': np.sinh,
    'COSH': np.cosh,
    'TANH': np.tanh,
    'ASINH': np.arcsinh,
    'ACOSH': np.arccosh,
    'ATANH': np.arctanh,
    'ASINH': np.arcsinh,
    'ACOS': np.arccos,
    'ATAN': np.arctan,
    # new in TunerPro 5.00.9503.00, published 12/22/21 - min,max,floor,ceil
    'MIN': np.min,
    'MAX': np.max,
    'FLOOR': np.floor,
    'CEIL': np.ceil,
    # XDF SPECIFIC
    # ...xdf general
    # ADDRESS, THIS, THAT
    # ...axis
    #'INDEX': lambda: None,
    #'INDEXES': lambda: None,
    #'CELL': lambda idx, precalc: None
    # ...table
    # ROW, COL, ROWS, COLS, CELL
  }
  
  def statement(self, args):
    # statement is terminal part of grammar, because we don't have multiple statements in TunerPro equations
    # ...but we have to return a `Tree` at the end of the day
    return args[0]
    #return args[0]

  @staticmethod
  def operation_call_tree(func: ConversionFunc, args: t.List[FunctionTreeNode]) -> FunctionTree:
    return FunctionTree(func, args)
  
  @v_args(inline=True)
  def func_call(self, name: lark.Token, args_tree: FunctionTree = None):
    function = self.function_registry[name.value.upper()]
    children: t.List[FunctionTreeNode] = args_tree.children # type: ignore
    return self.operation_call_tree(
      function,
      children
    )
  
  def bitwise_nand(self, args: t.List[FunctionTreeNode]) -> FunctionTreeNode:
    return FunctionCallTransformer.left_to_right_tree_single(
      int_truncated(
        lambda a, b: np.bitwise_not(np.bitwise_and(a, b))
      ),
      args
    )
  
  def bitwise_nor(self, args: t.List[FunctionTreeNode]) -> FunctionTree:
    return FunctionCallTransformer.left_to_right_tree_single(
      int_truncated(
        lambda a, b: np.bitwise_not(np.bitwise_or(a, b))
      ),
      args
    )
  
  def bitwise_or(self, args: t.List[FunctionTreeNode]) -> FunctionTree:
    return FunctionCallTransformer.left_to_right_tree_single(
      int_truncated(np.bitwise_or),
      args
    )
  
  def bitwise_xor(self, args: t.List[FunctionTreeNode]) -> FunctionTree:
    return FunctionCallTransformer.left_to_right_tree_single(
      int_truncated(np.bitwise_xor),
      args
    )
    
  def bitwise_and(self, args: t.List[FunctionTreeNode]) -> FunctionTree:
    return FunctionCallTransformer.left_to_right_tree_single(
      int_truncated(np.bitwise_and),
      args
    )
  
  def bitwise_shift(self, args: t.List[FunctionTreeNode]) -> FunctionTree:
    op_to_func: t.Dict[str, np.ufunc] = {
      '<<': np.left_shift,
      '>>': np.right_shift,
    }
    out = FunctionCallTransformer.left_to_right_tree(
      op_to_func,
      args,
      lambda arg: arg.data == 'shift_op'
    )
    return out
  
  @staticmethod
  def left_to_right_tree_single( 
    func: ConversionFunc, 
    args: t.List[FunctionTreeNode], 
  ) -> FunctionTree:
    func_tree_args: deque = deque()
    func_tree: FunctionTree = FunctionTree(None, []) # type: ignore
    for index, arg in enumerate(args):
      next = args.pop(index + 1) if len(args) > index + 1 else None
      new_args = [arg, next] if next else [arg]
      func_tree_args.extend(new_args)
      func_tree = FunctionCallTransformer.operation_call_tree(
        func,
        list(func_tree_args)
      )
      # reset args - intermediate tree is now an arg
      func_tree_args.clear()
      func_tree_args.append(func_tree)
    return func_tree

  @staticmethod
  def left_to_right_tree( 
    op_to_func: t.Dict[str, np.ufunc], 
    args: t.List[FunctionTreeNode], 
    condition: t.Callable[[FunctionTree], bool]
  ) -> FunctionTree:
    '''
    Returns a parse tree for left-to-right associative operators, e.g.:
    - mul_op: 5 % 2 * 3
    - comp_op: 5 && 2 || 3
    '''
    func_tree_args: deque = deque()
    func_tree: FunctionTree = FunctionTree(None, []) # type: ignore
    for index, arg in enumerate(args):
      if type(arg) == lark.Tree and condition(arg): # type: ignore
        token: lark.Token = arg.children[0] # type: ignore
        next = args.pop(index + 1)
        func_tree_args.append(next)
        func_tree = FunctionCallTransformer.operation_call_tree(
          op_to_func[token],
          list(func_tree_args)
        )
        # reset args - intermediate tree is now an arg
        func_tree_args.clear()
        func_tree_args.append(func_tree)
      else:
        func_tree_args.append(arg)
    return func_tree

  def comparison(self, args: t.List[FunctionTreeNode]) -> FunctionTree:
    op_to_func: t.Dict[str, np.ufunc] = {
      '<': np.less,
      '>': np.greater,
      '>=': np.greater_equal,
      '<=': np.less_equal,
      '==': np.equal,
      '!=': np.not_equal,
      '&&': np.logical_and,
      '||': np.logical_or,
    }
    # construct tree left-to-right
    out = FunctionCallTransformer.left_to_right_tree(
      op_to_func,
      args,
      lambda arg: arg.data == 'comp_op'
    )
    return out

  def term(self, args: t.List[FunctionTreeNode]) -> FunctionTree:
    op_to_func: t.Dict[str, np.ufunc] = {
      '*': np.multiply,
      '/': np.divide,
      '%': np.mod
    }
    out = FunctionCallTransformer.left_to_right_tree(
      op_to_func,
      args,
      lambda arg: arg.data == 'mul_op'
    )
    return out
  
  def arithmetic(self, args: t.List[FunctionTreeNode]) -> FunctionTree:
    # converts sum elements, which may be themselves typed, to list
    numerical_args: t.List[FunctionTreeNode] = []
    for index, arg in enumerate(args):
      if type(arg) == lark.Tree and arg.data == 'add_op':
        token: lark.Token = arg.children[0] # type: ignore
        # 'PLUS' token - take value as is...
        if token.type == 'MINUS':
          # pop next so we skip iteration, then negate for original sum
          to_negate: EquationArg = args.pop(index + 1) # type: ignore
          negate_call = self.operation_call_tree(
            np.negative,
            [to_negate]
          )
          numerical_args.append(negate_call)
          continue
      else:
        numerical_args.append(arg)
    # sum up the numerical args
    out = self.operation_call_tree(
      self.function_registry['SUM'],
      numerical_args
    )
    return out
  
  # factor, e.g. '-x', is the only unary op
  @v_args(inline = True)
  def factor(self, token_tree: lark.ParseTree, right: FunctionTreeNode):
    op_to_func: t.Dict[str, np.ufunc] = {
      '-': np.negative
    }
    token: lark.Token = token_tree.children[0] # type: ignore
    return self.operation_call_tree(
      op_to_func[token],
      [right]
    )
  
  # LITERALS
  # boolean literals TRUE/FALSE and numbers are literals with distinct parsing
  # logic, but will be classified more abstractly as Literal
  def true(self, args):
    return True
  
  def false(self, args):
    return False
  
  def number(self, args: t.List[lark.Token]) -> int | float:
    type, value = args[0].type, args[0].value
    if type == 'DEC_NUMBER':
      return int(value)
    elif type == 'HEX_NUMBER':
      return int(value, 16)
    elif type == 'FLOAT':
      return float(value)
    else:
      raise NotImplementedError