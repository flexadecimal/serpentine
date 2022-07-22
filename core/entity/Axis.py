from __future__ import annotations
from abc import ABC, abstractmethod
import typing as t
from core.entity import Table, Function
from .Base import (
  Base, CyclicReferenceException, Quantity, ArrayLike, Quantified, Formatted,
  UnitRegistry, XmlAbstractBaseMeta, xml_type_map, Array, RefersCyclically
)
from . import Xdf as xdf
from .EmbeddedData import Embedded
from .Math import Math
import numpy as np
from collections import ChainMap
from lxml import etree as xml
import pint

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
# `Function` gets only an `EmbeddedAxis`, but `Table`` can be a LabelAxis (a.k.a 'External (Manual)'), `LinkedAxis`, or `EmbeddedAxis`. Each exposes a different value access.
class Axis(AxisFormatted, Base, ABC, metaclass=XmlAbstractBaseMeta):
  Math: _math = Base.xpath_synonym('./MATH')
  id = Base.xpath_synonym('./@id')

class EmbeddedAxis(Axis, Embedded):
  pass

class XYLabelAxis(Axis, Quantified):
  labels: t.List[xml.ElementTree]= Base.xpath_synonym('./LABEL', many=True)
  # TODO: labels can be strings, int, or number depending on output type

  # provide value from labels, setter modifies XML
  @property
  def value(self) -> Quantity:
    out = [float(label.attrib['value']) for label in self.labels]
    return Quantity(Array(out), self.unit)

class AxisInterdependence(CyclicReferenceException):
  axis: XYLinkAxis
  
  def __init__(self, xdf: xdf.Xdf, table: Table.Table):
    self.xdf = xdf
    self.cycle = table
    self.axis = next(
      filter(
        lambda a: isinstance(a, XYLinkAxis) and a.linked is table,
        [table.x, table.y]
      )
    )
  
  def __str__(self):
        # fancy printing
    message = f"""In Xdf "{self.xdf._path}",

Table axis "{self.cycle.title}".{self.axis.id} refers to itself.
"""
    return message

class AxisLinked(RefersCyclically[AxisInterdependence], Axis, ABC, metaclass=XmlAbstractBaseMeta):
  '''
  Tables can have X/Y Axis linked to either:
  - Function (normalized, index 2)
  - Table (normalized, index 3) - depending on if you're defining row/col it will select that row/col from the table
  '''

  @classmethod
  @property
  def embed_type(self) -> str:
    '''
    Used in calculating `Axis` linking interdepenency.
    '''
    pass

  exception = AxisInterdependence
  
  @classmethod
  def dependency_graph(cls, xdf: xdf.Xdf):
    has_link = xdf.xpath(
      f"./XDFTABLE/XDFAXIS[@id='x' or @id='y'][.//embedinfo[@type='3' or @type='2']]"
    )
    graph = {
      # XML parent will be table, which must not be circular
      axis.linked: [axis.getparent()]
      for axis in has_link
    }
    return graph

  link_id = Base.xpath_synonym('./embedinfo/@linkobjid')
  @abstractmethod
  def linked(self):
    pass

class XYFunctionLinkAxis(AxisLinked, Quantified):
  embed_type = EmbedFormat[2]
  
  @property
  def linked(self) -> Function.Function:
    function_query = f"""
      //XDFFUNCTION[@uniqueid='{self.link_id}']
    """
    return self.xpath(function_query)[0]

  @property
  def value(self) -> Quantity:
    # this should be immutable - you can change the link, but not the value
    # see Var.LinkedVar.linked - this is similar, but no Constant
    # TODO - this needs a dependency tree like `Xdf._math_depedency_graph`
    return Quantity(self.linked.interpolated, self.unit)

class XYTableLinkAxis(AxisLinked, Quantified):
  embed_type = EmbedFormat[3]

  @property
  # they can be linked multiple times, e.g. 
  # linked -> linked -> linked -> label | embedded
  def linked(self) -> Table.Table:
    table_query = f"""
      //XDFTABLE[@uniqueid='{self.link_id}']
    """
    out = self.xpath(table_query)
    return out[0]

  @property
  def value(self) -> Quantity:
    '''
    With linked `Table`, Tunerpro implementation takes first column of table by default - irresepctive of whether this link is by an X or Axis.
    '''
    # take dimensionless, referencing `Axis` overrides unit
    out = self.linked.value.magnitude
    # table val may be one dimensional
    val = out if len(out.shape) == 1 else np.rot90(out)[0]
    return Quantity(val, self.unit)

# TODO: X/Y Axes can have stock units and data types, but Z axis does not? weird
class QuantifiedEmbeddedAxis(EmbeddedAxis, Quantified):
  @property
  def value(self) -> Quantity:
    original = EmbeddedAxis.value.fget(self) # type: ignore
    return Quantity(original, self.unit)

class FunctionAxis(QuantifiedEmbeddedAxis):
  @property
  def unit(self) -> t.Optional[pint.Unit]:
    '''
    E.g. RPM, Quarts, Seconds, Percent, etc.
    '''
    units: t.List[str] = self.xpath('./units/text()')
    key = units[0] if len(units)  > 0 else None
    invalid = UnitRegistry[None]
    # TODO: throw invalid unit error?
    out = UnitRegistry[key] if key and key in UnitRegistry else invalid
    return out

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
      return QuantifiedEmbeddedAxis
    # implicitly, only used in Table
    elif index == 2 or index == 3:
      # linkAxis, 2 normalized Function, 3 scaled parameter
      if index == 2:
        return XYFunctionLinkAxis
      else:
        return XYTableLinkAxis
  else:
    raise NotImplementedError('Invalid Axis embed type.')

XYLinkAxis = t.Union[XYFunctionLinkAxis, XYTableLinkAxis]
XYAxis = t.Union[QuantifiedEmbeddedAxis, XYLabelAxis, XYLinkAxis]