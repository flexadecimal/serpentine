from .common import *

from ..equation_parser import Equation
from lark import (
  UnexpectedInput
)

# see https://stackoverflow.com/questions/6098970/are-mixin-class-init-functions-not-automatically-called
# for a brief on this 'cooperative mixin' pattern
class EmbeddedMathMixin:
  '''
  Encapsulates the functionality in common between Constant and Axis - the
  parsing of math parameters from ECU .BIN files.
  
  The equation is parsed using a TunerPro-compatible namespace - in the
  definition, this is implicitly from BIN to logical format - this mixin saves the inverse, logical to BIN, so that higher-level logic is not bound to binary 
  details.
  '''
  
  # because of weird lxml `_init` api, we have to leave these as functions
  # rather than @property's so we can set them in _init
  
  def binary_data(self):
    embedded_data = self.xpath('./EMBEDDEDDATA')[0]
    #pdb.set_trace()
  
  @property
  def equation(self):
    math_element = self.xpath('./MATH')[0]
    equation_str = math_element.attrib['equation']
    try:
      equation_ast = Equation(equation_str)
      pdb.set_trace()
    except UnexpectedInput as error:
      print(equation_str)
      print(error)
      pdb.set_trace()
      pass
    return equation_ast