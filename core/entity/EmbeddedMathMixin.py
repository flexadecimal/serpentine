#from .common import *

# see https://stackoverflow.com/questions/6098970/are-mixin-class-init-functions-not-automatically-called
# for a brief on this 'cooperative mixin' pattern
class EmbeddedMathMixin(object):
  '''
  Encapsulates the functionality in common between Constant and Axis - the
  parsing of math parameters from ECU .BIN files.
  
  The equation is parsed using a TunerPro-compatible namespace - in the
  definition, this is implicitly from BIN to logical format - this mixin saves the inverse, logical to BIN, so that higher-level logic is not bound to binary 
  details.
  '''
  def __init__(self, 
  def binary_to_logical(equation):
    pass