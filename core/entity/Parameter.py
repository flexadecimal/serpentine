from .Base import Base, XmlAbstractBaseMeta, XdfRefMixin, ArrayLike
from abc import ABC, abstractmethod
import numpy as np
import numpy.typing as npt
import typing as T
from .Category import Categorized
from enum import Flag

class ParameterFlags(Flag):
  '''
  Controls optionally-clamped output.
  '''
  MIN_CLAMPED = 16
  MAX_CLAMPED = 32

class Parameter(Categorized, Base, XdfRefMixin, ABC, metaclass=XmlAbstractBaseMeta):
  id: str = Base.xpath_synonym('./@uniqueid')
  title: str = Base.xpath_synonym('./title/text()')
  description: T.Optional[str] = Base.xpath_synonym('./description/text()')
  # when None, always visible. TODO: actually implement
  @property
  def visibiity(self) -> T.Optional[int]:
    out = self.xpath('./@vislevel')
    return int(out[0]) if out else None

  def __repr__(self):
      return f"<{self.__class__.__qualname__} '{self.title}'>: {Base.__repr__(self)}"
      
 # def __repr__(self):
  #  filtered_vars = dict(filter(
  #    lambda key_val: key_val[0] != 'id',
  #    vars(self).items()
  #  ))
  #  return f"<{self.__class__.__qualname__} id='{self.id}'>{str(filtered_vars)}"

class Clamped(Base):
  '''
  For `Parameter`s like `Table` and `Constant` that have optional min/max clamped outputs.

  Constant uses xml <rangehlow>, <rangehigh> which is very strange. They also have defaults, per class.
  - Constant, Table.Axis: 0 - 255
  - Function.Axis: 0 - 1000

  TODO: implement defaults
  '''
  @property
  def flags(self) -> ParameterFlags:
    # if this was in Parameter class...
    #out = self.xpath('./@flags')
    # ... but actually we are in child of Parameter
    out = self.getparent().attrib['flags']
    return ParameterFlags(int(out, 16))
    
  @property
  def min(self) -> T.Optional[float]:
    out = self.xpath('./min/text()')
    return float(out[0]) if out and ParameterFlags.MIN_CLAMPED in self.flags else None
  
  @property
  def max(self) -> T.Optional[float]:
    out = self.xpath('./max/text()')
    return float(out[0]) if out and ParameterFlags.MAX_CLAMPED in self.flags else None

  def clamped(self, x: ArrayLike) -> ArrayLike:
    # either can be None, not both
    if not (self.min is None and self.max is None):
      return np.clip(x, self.min, self.max) # type: ignore
    else:
      return x