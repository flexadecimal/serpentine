from .Base import Base
from .EmbeddedData import EmbeddedMathMixin, Math
from .Parameter import Parameter
import numpy as np

class Constant(Parameter, EmbeddedMathMixin):
  '''
  XDF Constant, a.k.a. Scalar.
  '''
  Math: Math = Base.xpath_synonym('./MATH')

  @property
  def value(self):
    return self.Math.conversion_func(
      self.memory_map.astype(np.float, copy=False)
    )