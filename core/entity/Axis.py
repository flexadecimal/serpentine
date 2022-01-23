from __future__ import annotations
from abc import ABC, abstractmethod
import typing as t
from .Base import Base, Quantified, Quantity, ArrayLike, Formatted, XmlAbstractBaseMeta, xml_type_map, FormatOutput, Array, schemadef_index, friendly_schemadef_name
from .EmbeddedData import Embedded
from .Math import Math
import numpy as np
from collections import ChainMap
from lxml import etree as xml

# to avoid circular import
if t.TYPE_CHECKING:
  from .Function import Function

EmbedFormat: ChainMap[int, str] = xml_type_map(
  'embed_type'
)

# need this in `Axis` because python thinks we're referring to the property `Axis.Math`
_math = Math

class AxisFormatted(Formatted):
  '''
  Axes have the addition of an index count (when using manual labeling), or a link reference.
  '''
  @property
  def length(self) -> int:
    '''
    Axes set their length, which is also set in the <EMBEDDEDDATA> to render the value. Setter will modify both.
    '''
    return int(self.xpath('./indexcount/text()')[0])
  
  @property
  def source(self) -> str:
    '''
    Corresponds to `<embedinfo>` XML element - when `@type` is 2 or 3, the link is either a Function or linkable Parameter value.
    '''
    info = self.xpath('./embedinfo')
    # defaults to manual XML <LABEL>s
    name = EmbedFormat[int(info[0].attrib['type'])] if info else EmbedFormat[0]
    # if no embedinfo element, using the external manual <LABEL>s
    klass = Axis_class_from_element(self)
    return name

# DIFFERENT TYPES OF AXIS
# Function gets only an EmbeddedAxis, but Table can be a LabelAxis (a.k.a 'External (Manual)'), or LinkedAxis. Each exposes a different value access.
class Axis(AxisFormatted, Base, ABC, metaclass=XmlAbstractBaseMeta):
  Math: _math = Base.xpath_synonym('./MATH')
  id = Base.xpath_synonym('./@id')

  @property # type: ignore
  @abstractmethod
  def value(self) -> ArrayLike:
    pass

  # decorated property not supported by mypy, so ignore...
  @value.setter # type: ignore
  @abstractmethod 
  def value(self, value: ArrayLike) -> None:
    pass

  def __repr__(self):
    return f"<{self.__class__.__qualname__} '{self.title}'>: {Base.__repr__(self)}"

class EmbeddedAxis(Axis, Embedded):
  # each axis is a memory-mapped array
  @property
  def value(self):
    out = self.Math.conversion_func(
      self.memory_map.astype(
        np.float64,
        copy=False
        # use the underlying embedded row/col major ordering, shape, etc.
    ))
    return out

class XYLabelAxis(Axis, Quantified):
  labels: t.List[xml.ElementTree]= Base.xpath_synonym('./LABEL', many=True)
  # TODO: labels can be strings, int, or number depending on output type

  # provide value from labels, setter modifies XML
  @property
  def value(self) -> Quantity:
    out = [float(label.attrib['value']) for label in self.labels]
    return Quantity(Array(out), self.unit)

class XYLinkAxis(Axis, Quantified):
  '''
  Tables can have X/Y Axis linked to either:
  - Function (normalized, index 2)
  - Table (normalized, index 2) - depending on if you're defining row/col it will select that row/col from the table
  '''
  link_id = Base.xpath_synonym('./embedinfo/@linkobjid')

  @property
  # they can be linked multiple times, e.g. 
  # linked -> linked -> linked -> label | embedded
  def linked(self) -> t.Union[XYLinkAxis, XYLabelAxis, XYEmbeddedAxis]:
    table_query = f"""
      //XDFTABLE[@uniqueid='{self.link_id}']/XDFAXIS[@id='{self.id}']
    """
    function_query = f"""
      //XDFFUNCTION[@uniqueid='{self.link_id}']
    """
    # TODO - codify this XML enum somehow, nicer
    if self.source == EmbedFormat[2]:
      return self.xpath(function_query)[0]
    elif self.source == EmbedFormat[3]:
      return self.xpath(table_query)[0]
    else:
      raise NotImplementedError('Axis erroneously classified as linked.')

  @property
  def value(self) -> ArrayLike:
    # this should be immutable - you can change the link, but not the value
    # see Var.LinkedVar.linked - this is similar, but no Constant
    # TODO - this needs a dependency tree like `Xdf._math_depedency_graph`
    
    if self.source == EmbedFormat[2]:
    #if self.linked.__class__ is Function:
      # do normalization
      function = self.linked
      values, indices = function.x.value, function.y.value
      pass
      return function.value
    else:
      # output regular quantity
      out = self.linked.value
      if issubclass(out.__class__, Quantity):
        if self.unit and not out.unitless:
          return out.to(self.unit)
        else:
          return out
      else:
        return Quantity(out, self.unit)

# TODO: X/Y Axes can have stock units and data types, but Z axis does not? weird
class XYEmbeddedAxis(EmbeddedAxis, Quantified):
  '''
  Union of LabelAxis and EmbeddedAxis with quantities, that allows for switching the intrinsic type to either.
  '''
  @property
  def value(self) -> Quantity:
    original = EmbeddedAxis.value.fget(self) # type: ignore
    return Quantity(original, self.unit)

# used in `Xdf.XdfTyper`
def Axis_class_from_element(axis: xml.Element):
  children = axis.getchildren()
  # lxml.etree._ReadOnlyElementTree, used in type dispatch, doesnt have xpath :(
  # info = self.xpath('./embedinfo')
  info = next(filter(
    lambda el: el.tag == 'embedinfo',
    children
  ), None)
  labels = list(filter(
    lambda el: el.tag == 'LABEL',
    children
  ))
  # if LABELS, this is a LabelAxis
  if len(labels) > 0:
    return XYLabelAxis
  elif info is not None:
    index = int(info.attrib['type'])
    format = EmbedFormat[index]
    if index == 1:
      return XYEmbeddedAxis
    # implicitly, only used in Table
    elif index == 2 or index == 3:
      # linkAxis, 2 normalized Function, 3 scaled parameter
      return XYLinkAxis
  else:
    raise NotImplementedError('Invalid Axis embed type.')
