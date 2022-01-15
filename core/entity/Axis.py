import typing as T
from .Base import Base, QuantityMixin, Quantity, ArrayLike, FormattingMixin, xml_type_map
from .EmbeddedData import EmbeddedMathMixin
from .Math import Math
import numpy as np
from .Parameter import Parameter
from collections import ChainMap

# to avoid circular import
if T.TYPE_CHECKING:
  from .Function import Function

EmbedFormat: ChainMap[int, str] = xml_type_map(
  'embed_type'
)

# need this in `Axis` because python thinks we're referring to the property `Axis.Math`
_math = Math

class AxisFormattingMixin(FormattingMixin):
  '''
  Axes have the addition of an index count (when using manual labeling), or a link reference.
  '''
  @property
  def label_count(self) -> int:
    return int(self.xpath('./indexcount/text()')[0])
  
  @property
  def label_source(self) -> str:
    '''
    Corresponds to `<embedinfo>` XML element - when `@type` is 3 or 4, the link is either a Function or linkable Parameter value.
    '''
    info = self.xpath('./embedinfo')
    # if no embedinfo element, using the external manual <LABEL>s
    return EmbedFormat[int(info[0].attrib['type'])] if info else EmbedFormat[1]

class Axis(AxisFormattingMixin, EmbeddedMathMixin, Base):
  Labels = Base.xpath_synonym('./LABEL', many=True)
  Math: _math = Base.xpath_synonym('./MATH')

  # each axis is a memory-mapped array
  @property
  def value(self) -> ArrayLike:
    out = self.Math.conversion_func(
      self.memory_map.astype(
        np.float64, 
        copy=False
        # use the underlying embedded row/col major ordering, shape, etc.
    ))
    return out


# TODO: X/Y Axes can have stock units and data types, but Z axis does not? weird
class XYAxis(Axis, QuantityMixin):
  '''
  Table X/Y Axis with Labels from (following TunerPro parlance):
    - "Internal, Pure": binary memory map
    - "External (Manual)": <LABEL> elements
    - "Linked, Normalized": Parameter value, either Constant or Table
    - "Linked, Scale": TODO: figure out
  '''
  @property
  def length(self):
    return int(self.xpath('./indexcount/text()'))

  @property
  def value(self) -> Quantity:
    original = Axis.value.fget(self) # type: ignore
    return Quantity(original, self.unit)
