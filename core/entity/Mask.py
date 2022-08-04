import typing as t
from abc import ABC, abstractmethod
from .Base import XmlAbstractBaseMeta, Array
from .EmbeddedData import EmbeddedData
from .Math import Math
import numpy as np

# custom math subclasses for ZAxis with row/col
class Mask(np.ma.MaskType):
  def __repr__(self):
    # interpret masks as binary for space-saving printing
    return Array.__repr__(self.astype(np.int))

class MaskedMath(Math, ABC, metaclass=XmlAbstractBaseMeta):
  '''
  Specifically for `Table.ZAxis`, `<MATH>` elements with varying attributes must provide a Numpy mask to use in binary conversion.

  See the [Numpy documention on masked arrays](https://numpy.org/doc/stable/reference/maskedarray.html) for more details.

  TunerPro-style table equation matrix has the following `Math` elements in order of lowest to highest precedence. Calculation does not overlap - masks are excluded against others.

  - global table equation has no additional attributes,
  - row `Math` has row attribute,
  - col `Math` has column attirbute,
  - cell `Math` has both row and column.
  '''
  @property
  def shape(self):
    embedded_data: EmbeddedData = self.xpath('./preceding-sibling::EMBEDDEDDATA')[0]
    return embedded_data.shape
  
  @property
  @abstractmethod
  def mask(self) -> Mask:
    '''
    Numpy boolean mask array, following convention of `False` meaning valid data, and `True` meaning invalid data..
    '''
    pass