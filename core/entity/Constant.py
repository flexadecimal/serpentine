from .Base import Base, MeasurementMixin, Quantity
from .EmbeddedData import EmbeddedMathMixin
from .Math import Math
from .Parameter import Parameter
import numpy as np
import pint

class Constant(Parameter, EmbeddedMathMixin, MeasurementMixin):
  '''
  XDF Constant, a.k.a. Scalar.
  '''
  Math: Math = Base.xpath_synonym('./MATH')

  @property
  def value(self) -> Quantity:
    unitless = self.Math.conversion_func(self.memory_map.astype(np.float_, copy=False))
    return pint.Quantity(unitless, self.unit)