from __future__ import annotations
from abc import ABC, abstractmethod
import typing as t
from numpy.ma import MaskError
import numpy.typing as npt
from core.entity import Table, Function
from core.equation_parser.transformations.Evaluator import Evaluator
from core.equation_parser.transformations.FunctionCallTransformer import ConversionFunc, EquationArg, FunctionTree, NumericArg
from core.equation_parser.transformations.Replacer import NumericFunctionTree
from .Base import (
  Base, CyclicReferenceException, Quantified, Formatted,
  UnitRegistry, XmlAbstractBaseMeta, xml_type_map, Array, RefersCyclically
)
from . import Xdf as xdf
from .EmbeddedData import Embedded
from .Math import Math, null_accumulator
import numpy as np
from collections import ChainMap
from lxml import etree as xml
import pint
from ..equation_parser.transformations.TypeVisitors import TypeTransformer
from ..equation_parser.transformations.FunctionCallTransformer import (
  ConversionFunc, NumericArg, FunctionTree, GenericTree
)
from ..equation_parser.transformations import Replacer
import lark

EmbedFormat: ChainMap[int, str] = xml_type_map(
  'embed_type'
)

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

class EmbeddedAxisMath(Math):
  @property
  def _Axis(self) -> 'EmbeddedAxis':
    return self.getparent()

  @property
  def _accumulator(self):
    '''
    `XYEmbeddedAxis` conversion only has one equation.
    The given `accumulator` argument is the original memory map.
    For TunerPro compatibility, the "accumulator" is an all-0 axis,
    when in reality it should either:
    - be all `NaN`
    - raise an exception.
    TODO: toggleable `NaN`/exception/TunerPro "all-0" behavior
    '''
    out = null_accumulator(
      self._Axis.EmbeddedData.shape,
      0
    )
    return out

  def accumulate(self, accumulator: npt.NDArray) -> npt.NDArray:
    '''
    One-shot conversion accumulation is effectively a no-op.
    '''
    return self._accumulator

  @property
  def _namespace(self):
    return ChainMap(
      self._Axis._cell_namespace(self._accumulator),
      {
        'INDEX': self.index,
        'INDEXES': self.indexes
      }
    )

  def index(self):
    return np.arange(self._Axis.EmbeddedData.shape[0])

  def indexes(self):
    return self._Axis.EmbeddedData.shape[0]

# DIFFERENT TYPES OF AXIS
# `Function` gets only an `EmbeddedAxis`, but `Table`` can be a LabelAxis (a.k.a 'External (Manual)'), `LinkedAxis`, or `EmbeddedAxis`. Each exposes a different value access.
class Axis(AxisFormatted, Base, ABC, metaclass=XmlAbstractBaseMeta):
  id = Base.xpath_synonym('./@id')

default_fill = np.ma.default_fill_value(np.float_(0))
MaskedFunctionTree = GenericTree[ConversionFunc, t.Union[np.ma.masked_array, ConversionFunc]]
class UnbindCell(TypeTransformer[NumericFunctionTree, MaskedFunctionTree]):
  '''
  TunerPro "magic" - we need to emulate TunerPro's iterative
  equation processing by removing `cell` from the function tree, evaluating 
  the initial in its place (for TunerPro compatability, zeros), then substitute cell back in, e.g.:
  
  eq = "CELL(1; FALSE) + 2"
                            subsitute initial for cell - UnbindCell
  <function 'sum_args'>     <function 'sum_args'> -> [2, -, 2...]              
    <function 'cell'>          X = [0, -, 0...]      
      1                        2
      False
    2
  '''
  def __init__(self, initial: t.Optional[npt.ArrayLike]) -> None:
    self.initial = initial
    super().__init__(visit_tokens = False)

  # this 'function` dispatch is magic from `TypeVisitors`
  def function(self, args):
    # [func, *args]
    func, func_args = args
    if func.__name__ == 'cell':
      # we have an initial value, like [0, 0, 0...]
      if self.initial is not None:
        index = func_args[0]
        mask = np.full(self.initial.shape, False)
        mask[index] = True
        out = np.ma.masked_array(
          data=self.initial,
          mask=mask
        )
        # initial fill should not be set - mask value is frozen after first evaluation
        #out.fill_value = out.data[index]
        return out
      # we have just a var or something
      else:
        # implicit function argument
        return lark.Token('NAME', 'X')
    else:
      return MaskedFunctionTree(func, func_args)

  def __default__(self, data, children, meta):
    return MaskedFunctionTree(data, children, meta)

def unmask(x):
  return np.ma.filled(x)

def freeze(x, index: int):
  if x.fill_value == default_fill:
    # first evaluation - set fill
    x.fill_value = x.data[index]
  return np.ma.harden_mask(x)

class EmbeddedAxis(Axis, Embedded):
  # embedded Axis provides conversion namespace additions

  Math: 'EmbeddedAxisMath' = Base.xpath_synonym('./MATH')
  
  thinker = Evaluator().transform

  def _cell_namespace(self, accumulator: npt.NDArray):
    return {
      'CELL': self.cell_partial(accumulator)
    }

  def _cell_modify(self, instead: npt.ArrayLike, index: int, real_equation: NumericFunctionTree) -> NumericFunctionTree:
    '''
    Cell function AST  (calls to `cell` replaced with the initial value).

    evaluate - 
   caller will have to unmask, e.g.
   unmask -> [4, 2, 4...]
    <function 'sum_args'> -> [4, -, 4...]
      [2, -, 2...]
      2
  '''
    #                           unbound = 
    # <function 'sum_args'>     <function 'sum_args'> -> [2, -, 2...]         
    #   <function 'cell'>          X 
    #     1                        2
    #     False
    #   2
    unbound = UnbindCell(initial = None).transform(real_equation)
    # substitute initial-value evaluation back into unbound
    #  <function 'sum_args'> -> [4, -, 4...]
    #     <function 'sum_args'> = thunk
    #       initial = [0, -, 0...]
    #       2
    #     2

    # ...the thunk needs a hard mask; in this example, harden after first assignment of "2" on initial "0"
    thinker = Evaluator().transform
    thunk = MaskedFunctionTree(
      freeze,
      [UnbindCell(initial = instead).transform(real_equation), index]
    )
    # unmasking must be done by parent
    out = thunk
    substituted = Replacer.Replacer({'X': thunk}).transform(unbound)
    #out2 = NumericFunctionTree(unmask, [substituted])
    return out

  def cell_partial(self, initial: npt.NDArray):
    def cell(index: int, precalc: bool):
      '''
      TunerPro table axis cell lookup.

      TunerPro implements this differently on an edge case - if the Axis equation
      is something like `CELL(5; FALSE)`, `precalc=False` means we would be 
      returning an accumulated value when doing `ZAxis`, but in a regular `Axis`/`Constant`,
      there is only one equation - so the initial value is either:
      - TunerPro "all-0" array
      - array of `np.NaN` (strict mode, suppress exception)
      - raise Exception (strict mode, full)

      see `EmbeddedAxisMath._accumulator`.
      '''
      out = initial
      # TunerPro "magic" - we need to emulate TunerPro's iterative
      # equation processing by removing `cell` from the function tree, evaluating 
      # the initial in its place (for TunerPro compatability, zeros), then substitute cell back in
      #evaluated = Evaluator().transform(substituted)
      if precalc:
        out = np.full(self.EmbeddedData.shape, self.memory_map[index])
      else:
        raw = self.memory_map[index]
        # need numeric tree - args need to be bound here
        kwargs = self.Math.conversion_func.keywords
        replaced = Replacer.Replacer(self.Math.conversion_func.keywords).transform(self.Math.equation)
        # now do `CellEvaluator`, which will self-modify the AST
        substituted = self._cell_modify(initial, index, replaced)
        # and immediately evaluate
        return self.thinker(substituted)
      return out
    return cell

  def to_embedded(self, x: npt.NDArray):
    return self.Math.inverse_conversion_func(x)
  
  def from_embedded(self, x: npt.NDArray):
    return self.Math.conversion_func(x)

class XYLabelAxis(Axis, Quantified):
  labels: t.List[xml.ElementTree]= Base.xpath_synonym('./LABEL', many=True)
  # TODO: labels can be strings, int, or number depending on output type

  # provide value from labels, setter modifies XML
  @property
  def value(self) -> pint.Quantity:
    out = [float(label.attrib['value']) for label in self.labels]
    return pint.Quantity(Array(out), self.unit)

class AxisInterdependence(CyclicReferenceException):
  axis: XYLinkAxis
  
  def __init__(self, xdf: xdf.Xdf, table: Table.Table):
    self.xdf = xdf
    self.cycle = table
    self.axis = next(
      filter(
        lambda a: hasattr(a, "linked") and a.linked is table,
        [table.x, table.y]
      )
    )
  
  def __str__(self):
        # fancy printing
    message = f"""In Xdf "{self.xdf._path}",

Table axis "{self.cycle.title}".{self.axis.id} refers to itself.
"""
    return message

class AxisLinked(RefersCyclically[AxisInterdependence, Axis, Axis], Axis, ABC, metaclass=XmlAbstractBaseMeta):
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
  def dependency_graph(cls, xdf):
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
  
  @property
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
  def value(self) -> pint.Quantity:
    # this should be immutable - you can change the link, but not the value
    # see Var.LinkedVar.linked - this is similar, but no Constant
    # TODO - this needs a dependency tree like `Xdf._math_depedency_graph`
    return pint.Quantity(self.linked.interpolated, self.unit)

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
  def value(self) -> pint.Quantity:
    '''
    With linked `Table`, Tunerpro implementation takes first column of table by default - irresepctive of whether this link is by an X or Axis.
    '''
    # take dimensionless, referencing `Axis` overrides unit
    out = self.linked.value.magnitude
    # table val may be one dimensional
    val = out if len(out.shape) == 1 else np.rot90(out)[0]
    return pint.Quantity(val, self.unit)

# TODO: X/Y Axes can have stock units and data types, but Z axis does not? weird
class QuantifiedEmbeddedAxis(EmbeddedAxis, Quantified):
  @property
  def value(self) -> pint.Quantity:
    original = EmbeddedAxis.value.fget(self) # type: ignore
    return pint.Quantity(original, self.unit)
  
  @value.setter
  def value(self, value: pint.Quantity):
    in_val = value.magnitude
    return EmbeddedAxis.value.fset(self, in_val) # type: ignore

class XYEmbeddedAxis(QuantifiedEmbeddedAxis):
  pass

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
      return XYEmbeddedAxis
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
XYAxis = t.Union[XYEmbeddedAxis, XYLabelAxis, XYLinkAxis]