from __future__ import annotations
from abc import ABC, abstractmethod
from multiprocessing import BoundedSemaphore
import typing as t
from .Base import Base, Quantified, Quantity, ArrayLike, Formatted, XmlAbstractBaseMeta, xml_type_map, Array
from .EmbeddedData import Embedded
from .Math import Math
import numpy as np
from collections import ChainMap
from lxml import etree as xml
from decimal import Decimal, ROUND_HALF_UP
import itertools as it

# to avoid circular import
if t.TYPE_CHECKING:
  from .Function import Function

EmbedFormat: ChainMap[int, str] = xml_type_map(
  'embed_type'
)

# need this in `Axis` because python thinks we're referring to the property `Axis.Math`
_math = Math

def increasing(a: Array) -> np.ma.masked_array:
  '''
  Retain monotonically-increasing subset by masking out values that fall below the max, e.g.
  `[0, 1, 2, 0, -2, 4, 0, -5, 6, 7, 8]` => 
  `[0, 1, 2, -,  -, 4, -,  -, 6, 7, 8]`
  '''
  # https://stackoverflow.com/a/28563925
  high_water = np.maximum.accumulate(a)
  fall_under = high_water - a > 0
  out: np.ma.masked_array = np.ma.masked_array(a, fall_under)
  return out

def gaps(indices: np.ma.masked_array, vals: np.ma.masked_array) -> np.ma.masked_array:
  # [[idx1, val1], [idx2, val2]...]
  idxVal = np.stack(
    (
      round(indices.compressed()),
      vals.compressed()  
    ),
    axis = 1
  )
  # ...indices paired, e.g. [0, 1, 2] -> [0, 1], [1, 2], [2, 3]
  pairs = np.lib.stride_tricks.sliding_window_view(
    np.rot90(idxVal)[1],
    2
  )
  # ...list of idx, val, slice width - greater than one means this is a discontinuity
  boundsAndDiff = np.hstack((pairs, np.diff(pairs)))
  # ...(start, end, diff > 2) means out[start + 1: end] is the non-inclusive empty slice, e.g. [1, 2, 0, -1, 3] 
  gaps = boundsAndDiff[boundsAndDiff[:, 2] > 1]
  return gaps


def round_off(number, ndigits=None):
    """
    Always round off. TunerPro indexing always arounds 0.5 => 1
    See https://stackoverflow.com/a/70285861.
    """
    exp = Decimal('1.{}'.format(ndigits * '0')) if ndigits else Decimal('1')
    return type(number)(Decimal(number).quantize(exp, ROUND_HALF_UP))

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


# TODO: use tunerpro round? 0.5 => 1 always
def round(a: Array) -> Array:
  return np.around(a, decimals = 0)

def monotone_interpolated(values: Array, indices: Array) -> Array:
  '''
  TunerPro uses a unique interpolation strategy when using `Function` as an axis. 
  Fill in the monotone parts using the indices and their matching value, and interpolate the non-monotone parts using the previous value/
  
  v idx     out
  10	0  |   10
  20	1  |   20
  30	2  |   30
  40  3  |   40
  50	0  -    68     np.linspace(60, 70, abs(4.5-0))
  60  0  -    
  70 4.5 |   70
  80  6  |   80
  90  2  -    109.23 np.linspace(100, 110, abs(8 - -5))
  100	-5 -   110
  110 8  |   120
  120 9  |   130
  130 10 |   157.65
  140 -5 -    158.24
  150 -2 -    158.82
         -    159.41
  160 15 |   160
  '''
  # ...segregate increasing subsequences in indices
  monotonic_idx = increasing(indices)
  monotonic_val: np.ma.masked_array = np.ma.masked_array(values, monotonic_idx.mask)
  non_monotonic_idx: np.ma.masked_array = np.ma.masked_array(
    data=indices,
    mask=np.logical_not(monotonic_idx.mask)
  )
  #non_monotonic_val = np.ma.masked_array(
  #  data=values,
  #  mask=non_monotonic_idx.mask
  #)
  #  FILL IN THE BLANKS
  out: Array = Array(np.zeros(values.shape))
  # ...list of idx, val, e.g. [[0, 10], [1, 20]]
  uninterpolated = np.stack(
    (
      round(monotonic_idx.compressed()),
      monotonic_val.compressed()  
    ),
    axis = 1
  )
  # ...indices paired, e.g. [0, 1, 2] -> [0, 1], [1, 2], [2, 3]
  pairs = np.lib.stride_tricks.sliding_window_view(
    np.rot90(uninterpolated)[1],
    2
  )
  # ...list of idx, val, slice width - greater than one means this is a discontinuity
  boundsAndDiff = np.hstack((pairs, np.diff(pairs)))
  # ...(start, end, diff > 2) means out[start + 1: end] is the non-inclusive empty slice, e.g. [1, 2, 0, -1, 3] 
  gaps = boundsAndDiff[boundsAndDiff[:, 2] > 1]
  adjust_start = np.full_like(np.zeros(gaps.shape), [1, 0, 0])
  gaps = gaps + adjust_start
  # fill output with each index's matching value from function
  for index, val in uninterpolated:
    out[int(index)] = val
  # traverse gaps backwards
  #gaps = np.hstack((enumerated, np.flipud(gaps)))
  # for interpolation, fill in empty parts
  clean_indices = round(indices).astype(np.integer)
  for start, end, diff in gaps.astype(np.integer):
    gap = out[start:end]
    rising = np.flatnonzero(values == out[end])[0] - 1, end
    length = abs(
      clean_indices[rising[0] + 1] - clean_indices[rising[0]]
    )
    interpolant = np.linspace(
    # interpolate between end-of-dip value and indexed value
      values[rising[0]], out[rising[1]],
      # length between end of dip coords
      length,
      endpoint = False
    )
    # now take the tail of the full interpoland to fill the gap
    filler = interpolant[-(diff - 1):]
    out[start: end] = filler    
  return out

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
  def linked(self) -> t.Union[XYLinkAxis, XYLabelAxis, QuantifiedEmbeddedAxis]:
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
  def value(self):
    # this should be immutable - you can change the link, but not the value
    # see Var.LinkedVar.linked - this is similar, but no Constant
    # TODO - this needs a dependency tree like `Xdf._math_depedency_graph`
    if self.source == EmbedFormat[2]:
    #if self.linked.__class__ is Function:
      # DO NORMALIZATION...
      function = self.linked
      values, indices = function.x.value, function.y.value
      return monotone_interpolated(values, indices)
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
class QuantifiedEmbeddedAxis(EmbeddedAxis, Quantified):
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
      return QuantifiedEmbeddedAxis
    # implicitly, only used in Table
    elif index == 2 or index == 3:
      # linkAxis, 2 normalized Function, 3 scaled parameter
      return XYLinkAxis
  else:
    raise NotImplementedError('Invalid Axis embed type.')
