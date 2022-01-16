from .Base import Base, XmlAbstractBaseMeta, XdfRefMixin, ArrayLike
from abc import ABC, abstractmethod
import numpy as np
import typing as T
from .Category import Categorized

class Parameter(Categorized, Base, XdfRefMixin, ABC, metaclass=XmlAbstractBaseMeta):
  id: str = Base.xpath_synonym('./@uniqueid')
  title: str = Base.xpath_synonym('./title/text()')
  description: T.Optional[str] = Base.xpath_synonym('./description/text()')
  # TODO: codify using XDF-local enum?
  # see https://docs.python.org/3/library/enum.html#functional-api
  Category = Base.xpath_synonym('./CATEGORYMEM')

  @property
  @abstractmethod
  def value(self) -> ArrayLike:
      '''
      XDF parameters, using their `<MATH>` equation data, convert binary data to a numerical value - 
      right now, these are only `XDFCONSTANT` and `XDFTABLE`. `XDFTABLE` parses 3 axes to form a surface,
      and `XDFCONSTANT` need just parse one. These numerical values can then be referenced in other equations.
      '''
      pass

  def __repr__(self):
      return f"<{self.__class__.__qualname__} '{self.title}'>: {Base.__repr__(self)}"
      
 # def __repr__(self):
  #  filtered_vars = dict(filter(
  #    lambda key_val: key_val[0] != 'id',
  #    vars(self).items()
  #  ))
  #  return f"<{self.__class__.__qualname__} id='{self.id}'>{str(filtered_vars)}"

class ClampedMixin(Base):
  '''
  For `Parameter`s like `Table` and `Constant` that have optional min/max clamped outputs.

  Constant uses xml <rangehlow>, <rangehigh> which is very strange. They also have defaults, per class.
  - Constant, Table.Axis: 0 - 255
  - Function.Axis: 0 - 1000
  '''
  @property
  def min(self) -> T.Optional[float]:
    out = self.xpath('./min/text()')
    return float(out[0]) if out else None
  
  @property
  def max(self) -> T.Optional[float]:
    out = self.xpath('./max/text()')
    return float(out[0]) if out else None

  def clamped(self, x: ArrayLike) -> ArrayLike:
    # either can be None, not both
    if not (self.min is None and self.max is None):
        return np.clip(x, self.min, self.max) # type: ignore
    else:
      return x