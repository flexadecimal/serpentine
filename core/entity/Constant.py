from collections import ChainMap
from . import Base, Math
from .EmbeddedData import Embedded
from .Parameter import Parameter, Clamped
import numpy as np
import numpy.typing as npt
import pint
import typing as t

class ConstantMath(Math.Math):
  def accumulate(self, accumulator: npt.NDArray) -> npt.NDArray:
    return accumulator

  def _namespace(self):
    return ChainMap()

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

class Constant(Parameter, Embedded, Base.Formatted, Base.Quantified, ConstantClamped):
  '''
  XDF Constant, a.k.a. Scalar.
  '''
  Math: ConstantMath = Base.Base.xpath_synonym('./MATH')

  @property
  def value(self) -> pint.Quantity:
    return pint.Quantity(Embedded.value.fget(self), self.unit)

  @value.setter
  def value(self, value: pint.Quantity):
    return Embedded.value.fset(self, value)
  
  def to_embedded(self, x: npt.NDArray):
    return self.Math.conversion_func(x)
  
  def from_embedded(self, x: npt.NDArray):
    return self.Math.inverse_conversion_func(x)
