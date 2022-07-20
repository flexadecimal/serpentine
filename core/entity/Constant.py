from core.entity.Axis import QuantifiedEmbeddedAxis
from .Base import Base, Quantified, Quantity, Formatted
from .EmbeddedData import Embedded, EmbeddedValueError
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
  @property
  def value(self) -> pint.Quantity:
    return Quantity(Embedded.value.fget(self), self.unit) # type: ignore

  @value.setter
  def value(self, value):
    return Embedded.value.fset(self, value)
