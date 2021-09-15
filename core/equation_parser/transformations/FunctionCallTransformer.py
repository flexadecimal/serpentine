import enum
import typing as T
from lark import Tree, Token
from lark.visitors import (
  Transformer,
  v_args
)
import numpy as np
import numpy.typing as npt
import functools
from collections import deque

class FunctionCallTransformer(Transformer):
  '''
  Transforms an equation AST (abstract syntax tree) to one with vectorized numpy functions. This is an intermediate syntactical form - the arguments must still processed as functions by calling along the tree.
  '''
  @staticmethod
  def if_func(condition: bool, true_val: T.Any, false_val: T.Any) -> T.Any:
    return true_val if condition else false_val

  # so we dont have to do fancy type dispatch on args, a version of sum that
  # takes variable arguments
  @staticmethod
  def sum_args(*args) -> npt.ArrayLike:
    return functools.reduce(np.add, args)

  # DISPATCH TABLE
  # python weirdness - staticmethod callables are in __func__
  # TODO: functions return number or Union[number, ref], where refs are
  # the XDF functions?
  function_registry: T.Dict[str, T.Callable[..., npt.ArrayLike]] = {
    # MATH FUNCTIONS
    'ABS': np.abs,
    'AVG': np.average,
    'EXP': np.exp,
    'LOG': np.log,
    'POW': np.float_power,
    'SQR': np.sqrt,
    'SUM': sum_args.__func__, # type: ignore
    'LOG10': np.log10,
    'RADIANS': np.radians,
    'DEGREES': np.degrees,
    'IF': if_func.__func__, # type: ignore
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
    # XDF SPECIFIC
    # ...axis
    #'INDEX': lambda: None,
    #'INDEXES': lambda: None,
    #'CELL': lambda idx, precalc: None
  }
  
  # TODO - get signature from core/Math.ConversionFuncType?
  @staticmethod
  def operation_call_tree(func: T.Callable, args: T.List) -> Tree:
    # this is to be ignored - we put typed things, but Lark only wants strings
    return Tree(func, args) # type: ignore
  
  @v_args(inline=True)
  def func_call(self, name: Token, args_tree: Tree = None):
    function = self.function_registry[name.value.upper()] if name.value.upper() \
    in self.function_registry else name.value.upper()
    return self.operation_call_tree(
      function,
      args_tree.children if args_tree else []
    )
  
  def bitwise_nand(self, args: T.List):
    # lambda late bound, linter can't check
    return self.operation_call_tree(
      lambda x: np.logical_not(np.logical_and(x)), # type: ignore
      args
    )
  
  def bitwise_nor(self, args: T.List):
    return self.operation_call_tree(
      lambda x: np.logical_not(np.logical_or(x)), # type: ignore
      args
    )
    
  def bitwise_or(self, args: T.List):
    return self.operation_call_tree(np.logical_or, args)
  
  def bitwise_xor(self, args: T.List):
    return self.operation_call_tree(np.logical_xor, args)
    
  def bitwise_and(self, args: T.List):
    return self.operation_call_tree(np.logical_and, args)
  
  def bitwise_shift(self, args: T.List):
    op_to_func: T.Dict[str, T.Callable] = {
      '<<': np.left_shift,
      '>>': np.right_shift,
    }
    # in parse order, first arg is left side, second is operator, third is right side
    operator_tree = args[1]
    operator = operator_tree.children[0].value
    # idiomatic to use remove here, although not really 'functional'
    args.remove(operator_tree)
    return self.operation_call_tree(
      op_to_func[operator],
      args
    )
  
  @v_args(inline=True)
  def comparison(self, left, token_tree: Tree, right):
    op_to_func: T.Dict[str, T.Callable] = {
      '<': np.less,
      '>': np.greater,
      '>=': np.greater_equal,
      '<=': np.less_equal,
      '==': np.equal,
      '!=': np.not_equal,
      '&&': np.logical_and,
      '||': np.logical_or,
    }
    return self.operation_call_tree(
      # we have to ignore here because children is only list of token, but not typed that way
      op_to_func[token_tree.children[0]], # type: ignore
      [left, right]
    )  

  def term(self, args):
    op_to_func: T.Dict[str, T.Callable] = {
      '*': np.multiply,
      '/': np.divide,
      '%': np.mod
    }
    # construct tree left-to-right
    func_tree_args = deque()
    func_tree = Tree(None, [])
    for index, arg in enumerate(args):
      if type(arg) == Tree and arg.data == 'mul_op':
        token = arg.children[0]
        next = args.pop(index + 1)
        func_tree_args.append(next)
        func_tree = self.operation_call_tree(
          op_to_func[token],
          list(func_tree_args)
        )
        # reset args - intermediate tree is now an arg
        func_tree_args.clear()
        func_tree_args.append(func_tree)
      else:
        func_tree_args.append(arg)

    return func_tree
  
  def arithmetic(self, args):
    # converts sum elements, which may be themselves typed, to list
    numerical_args = []
    for index, arg in enumerate(args):
      if type(arg) == Tree and arg.data == 'add_op':
        token = arg.children[0]
        # 'PLUS' token - take value as is...
        if token.type == 'MINUS':
          # pop next so we skip iteration, then negate for original sum
          to_negate = args.pop(index + 1)
          negate_call = self.operation_call_tree(
            np.negative,
            [to_negate]
          )
          numerical_args.append(negate_call)
          continue
      else:
        numerical_args.append(arg)
    # sum up the numerical args
    return self.operation_call_tree(
      self.function_registry['SUM'],
      numerical_args
    )
  
  # factor, e.g. '-x', is the only unary op
  @v_args(inline = True)
  def factor(self, token: Tree, right):
    op_to_func = {
      '-': np.negative
    }
    return self.operation_call_tree(
      op_to_func[token.children[0]], # type: ignore
      [right]
    )
  
  # LITERALS
  # boolean literals TRUE/FALSE and numbers are literals with distinct parsing
  # logic, but will be classified more abstractly as Literal
  def true(self, args):
    return True
  
  def false(self, args):
    return False
  
  def number(self, args: T.List[Token]):
    type, value = args[0].type, args[0].value
    if type == 'DEC_NUMBER':
      return int(value)
    elif type == 'HEX_NUMBER':
      return int(value, 16)
    elif type == 'FLOAT':
      return float(value)
    else:
      raise NotImplementedError