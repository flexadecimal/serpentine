# friendly Equation class that holds the trees in memory
# Table, Parameter, Constant will have this as member
from .common import *

from functools import reduce
import operator

class Equation(object):
  '''
  Container for syntax tree operations for equations used in binary data conversion.
  '''
  def __init__(self, equation):
    self.tree = expression_tree(equation)
  
  @staticmethod
  def apply_pipeline(source, *transformation_instances):
    # chaining transformations, see:
    # https://lark-parser.readthedocs.io/en/latest/visitors.html#visitor
    combined = reduce(operator.mul, transformation_instances)
    return combined.transform(source)
  
  @staticmethod
  def print(tree):
    printer = transformations['Printer'](visit_tokens = True)
    stringified = printer.transform(tree)
    print(stringified.pretty())
  
  @property
  def numpified(self):
    return self.apply_pipeline(
      self.tree,
      transformations['FunctionCallTransformer'](visit_tokens = True),
    )
  
  @property
  def inverted(self):
    return self.apply_pipeline(
      self.tree,
      transformations['FunctionCallTransformer'](visit_tokens = True),
      #transformations['VarBinder'](visit_tokens = True),
      #transformations['Inverter']()
    )