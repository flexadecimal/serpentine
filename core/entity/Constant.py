from .Base import Base, Quantified, Quantity, Formatted
from .EmbeddedData import Embedded
from .Math import Math
from .Parameter import Parameter, Clamped
import numpy as np
import pint
import typing as t

# weird TunerPro bullshit - only Constant needs to override min/max with rangehigh/rangelow
class ConstantClamped(Clamped):
  @property
  def min(self) -> t.Optional[float]:
    out = self.xpath('./rangelow/text()')
    return float(out[0]) if out else None

  @property
  def max(self) -> t.Optional[float]:
    out = self.xpath('./rangehigh/text()')
    return float(out[0]) if out else None


class Constant(Parameter, Embedded, Formatted, Quantified, ConstantClamped):
  '''
  XDF Constant, a.k.a. Scalar.
  '''
  Math: Math = Base.xpath_synonym('./MATH')

  @property
  def value(self) -> Quantity:
    unitless = self.Math.conversion_func(
      self.memory_map.astype(np.float_, copy=False)
    )
    return pint.Quantity(self.clamped(unitless), self.unit)

  @value.setter
  def value(self, value):
    out = np.array([self.Math.inverse_conversion_func(value)])
    # write to map
    # see https://numpy.org/devdocs/reference/generated/numpy.memmap.html
    # this will implicitly truncate floats
    self.memory_map[:] = np.array([out])[:]
    # flush ? 
    #self.memory_map.flush()