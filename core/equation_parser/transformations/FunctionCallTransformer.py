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

class FunctionCallTransformer(Transformer):
  '''
  Transforms an equation AST (abstract syntax tree) to one with vectorized numpy functions, such that it can be interpreted in "forwards" or "reverse"
  fashion for binary-to-measure conversion.
  '''
  @staticmethod
  def if_func(condition, true_val, false_val):
    return true_val if condition else false_val

  # dispatch table
  function_registry = {
    # math functions
    'ABS': np.abs,
    'AVG': np.average,
    'EXP': np.exp,
    'LOG': np.log,
    'POW': np.float_power,
    'SQR': np.sqrt,
    'SUM': np.sum,
    'LOG10': np.log10,
    'RADIANS': np.radians,
    'DEGREES': np.degrees,
    'IF': if_func,
    'ROUND': round,
    'MROUND': lambda a, b: a // b,
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
  
  @staticmethod
  def operation_call_tree(func, args):
    return Tree(func, args)
  
  @v_args(inline=True)
  def func_call(self, name_token, args_tree=None):
    function = self.function_registry[name_token.value] if name_token.value \
    in self.function_registry else name_token.value
    return self.operation_call_tree(
      function,
      args_tree.children if args_tree else []
    )
  
  def bitwise_nand(self, args):
    return self.operation_call_tree(
      lambda x: np.logical_not(np.logical_and(x)),
      args
    )
  
  def bitwise_nor(self, args):
    return self.operation_call_tree(
      lambda x: np.logical_not(np.logical_or(x)),
      args
    )
    
  def bitwise_or(self, args):
    return self.operation_call_tree(np.logical_or, args)
  
  def bitwise_xor(self, args):
    return self.operation_call_tree(np.logical_xor, args)
    
  def bitwise_and(self, args):
    return self.operation_call_tree(np.logical_and, args)
  
  def bitwise_shift(self, args):
    op_to_func = {
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
  def comparison(self, left, token_tree, right):
    op_to_func = {
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
      op_to_func[token_tree.children[0].value],
      [left, right]
    )  
  
  @v_args(inline=True)
  def term(self, left, op_token, right):
    op_to_func = {
      '*': np.multiply,
      '/': np.divide,
      '^': np.mod
    }
    return self.operation_call_tree(
      op_to_func[op_token.children[0].value],
      [left, right]
    )
  
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
      np.sum,
      numerical_args
    )
  
  def number(self, args):
    type, value = args[0].type, args[0].value
    if type == 'DEC_NUMBER':
      return int(value)
    elif type == 'HEX_NUMBER':
      return int(value, 16)
    elif type == 'FLOAT':
      return float(value)
    else:
      raise NotImplementedError