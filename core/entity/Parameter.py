from .Base import Base, XmlAbstractBaseMeta, XdfRefMixin, Array
from abc import ABC, abstractmethod
import numpy as np
import numpy.typing as npt
import typing as T

class Parameter(Base, XdfRefMixin, ABC, metaclass=XmlAbstractBaseMeta):
  id: str = Base.xpath_synonym('./@uniqueid')
  title: str = Base.xpath_synonym('./title/text()')
  description: T.Optional[str] = Base.xpath_synonym('./description/text()')
  # TODO: codify using XDF-local enum?
  # see https://docs.python.org/3/library/enum.html#functional-api
  Category = Base.xpath_synonym('./CATEGORYMEM')

  @property
  @abstractmethod
  def value(self) -> Array:
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