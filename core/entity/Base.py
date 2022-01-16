from __future__ import annotations
import typing as t
from lxml import (
  etree as xml,
  objectify,
)
import itertools as it
import numpy as np
import numpy.typing as npt
import pint
from abc import ABC
import functools
from collections import ChainMap
from pathlib import Path
import os
import re
from enum import Enum

# to avoid circular import for XDF self-reference
if t.TYPE_CHECKING:
  from .Xdf import Xdf

XmlBase = xml.ElementBase
#XmlBase = objectify.ObjectifiedDataElement

class XmlClassMeta(type):
  @staticmethod
  def property_funcs(dikt, bases):
    base_descendant = it.takewhile(
      lambda base: base != XmlBase,
      bases
    )
    # child dict union with inherited bases' dicts
    lineage_vars = functools.reduce(
      lambda a, b: a | b,
      map(lambda base: base.__dict__, base_descendant),
      dikt
    )
    property_funcs = list(filter(
      lambda key_val: type(key_val[1]) == property,
      lineage_vars.items()
    ))
    return property_funcs
  
  def __new__(cls, name, bases, dikt):
    new_dict = {}
    if __debug__:
      new_dict['__property_funcs__'] = XmlClassMeta.property_funcs(dikt, bases)
    
    klass = super().__new__(cls, name, bases, dikt | new_dict)
    return klass

class Base(XmlBase, metaclass=XmlClassMeta): # type: ignore
  '''
  LXML ElementBase custom base class entities.
  tODO:
  - json serialization for API
  - read/write binding to XML structure
  '''
  @staticmethod
  def __xpath_dispatch(element, xpath_expression, many):
    result = element.xpath(xpath_expression)
    if len(result) == 0 and not many:
      return None
    elif len(result) == 1 and not many:
      return result[0]
    else:
      return result
  
  @classmethod
  def xpath_synonym(cls, xpath_expression, many = False, collection_class=dict):
    '''
    type-generic binding to lxml element, e.g. Axes -> XDFAXIS
    '''
    return property(
      # getter
      lambda self: Base.__xpath_dispatch(self, xpath_expression, many),
      # setter
      lambda self, val: setattr(self, '', val)
      # deleter
      #lambda self, name: 
    )
  
  # custom init, see:
  # https://lxml.de/element_classes.html#setting-up-a-class-lookup-scheme
  # remember - self is an xml element, so has .xpath(), .attrib, etc.
  #def _init(self):
  #  if __debug__:
  #    # eager init @property's, so they can be shown in vars
  #    for name, val in self.__property_funcs__:
  #      self.__dict__[name] = val.__get__(self)
    
  def __str__(self):
    return objectify.dump(self)
  
  def __repr__(self):
    return self.getroottree().getpath(self)

class XmlAbstractBaseMeta(type(Base), type(ABC)): #type: ignore
  '''
  For Python class weirdness - see [this StackOverFlow answer](https://stackoverflow.com/a/61350480).

  Children of `Base` that are abstract must use this metaclass rather than `ABCMeta` directly, e.g.:
  ```
  Var(Base):
    @abstractmethod
    def foo()
      ...

  LinkedVar(Var, ABC, metaclass=XmlAbstractBaseMeta):
    ...
  ```
  '''
  pass

class XdfRefMixin:
  '''
  Utility Mixin class that provides the `_xdf` reference to the containing document.
  '''
  @property
  def _xdf(self: t.Any) -> Xdf:
    return self.xpath("/XDFFORMAT")[0]

# stolen from numpy.typing
ScalarType = t.TypeVar("ScalarType", bound=np.generic, covariant=True)
class Array(np.ndarray, t.Generic[ScalarType]):
  '''
  Custom `numpy.ndarray` subclass with debug friendly stuff.
  See https://numpy.org/doc/stable/user/basics.subclassing.html?highlight=arange#simple-example-adding-an-extra-attribute-to-ndarray.
  '''
  def __new__(cls, arr):
    obj = np.asarray(arr).view(cls)
    # set additional stuff here....
    return obj

  def __array_finalize__(self, obj):
    # see InfoArray.__array_finalize__ for comments
    if obj is None: return
    #self.info = getattr(obj, 'info', None)

  def __repr__(self):
    return np.array2string(self, max_line_width=np.inf)

# measurements/units singleton instantiated at import-time
core_path = Path(__file__).parent.parent
schemata_path = os.path.join(core_path, 'schemata')
type_schema_path = 'tunerpro_types.xsd'
type_schema = xml.parse(os.path.join(schemata_path, type_schema_path))
namespaces = type_schema.getroot().nsmap


def friendly_schemadef_name(el: xml.Element) -> str:
  return el.xpath("./xs:annotation/xs:appinfo[1]/text()", namespaces=namespaces)[0]

def schemadef_index(el: xml.Element) -> int:
  base = el.xpath("./ancestor::xs:restriction/@base", namespaces = namespaces)[0]
  if base == 'xs:integer':
    return int(el.attrib['value'])
  #elif base == 'xs:float':
  # convert to integer prefix value
  return int(float(el.attrib['value']))

class UnitDef(t.NamedTuple):
  friendly_name: str
  unit: t.Optional[pint.Unit]
 
def xml_type_map(
  xml_type: str, 
  # for enum key, use index
  key: t.Callable[[xml.Element], t.Any] = schemadef_index,
  # by default, use friendly name
  val: t.Callable[[xml.Element], t.Any] = friendly_schemadef_name,
  extends: t.Iterable[ChainMap[int, t.Any]] = [],
) -> ChainMap[int, t.Any]:
  elements = type_schema.xpath(
    f"//xs:simpleType[@name='{xml_type}']//xs:enumeration", 
    namespaces=namespaces
  )
  # pint unit - key is (index, friendly): unit
  self_members = {key(el): val(el) for el in elements}
  return ChainMap(self_members, *extends)

# construct Pint definitions here...
ureg = pint.UnitRegistry(
  # don't use default Pint definitions
  filename=None,
  case_sensitive=False
)
pint_first_def_regex = rf"(?:(?P<alias>@alias) )?(?P<name>\w+)-?.*"
def pintify(el: xml.Element, unit = True) -> t.Optional[pint.Unit]:
  # second appinfo - newline seperated list of definitions, to append friendly alias to
  defs = el.xpath("./xs:annotation/xs:appinfo[2]/text()", namespaces=namespaces)
  # ...there may be no defs if option is a unitless value like Percent or Duty Cycle
  if len(defs) > 0:
    lines = list(map(
      lambda l: l.strip(),
      defs[0].strip().split("\n")
    ))
    # add friendly alias to last definition, implicity the final def
    last_def = lines[-1]
    # ...TODO: INDEX UNIT WITH FRIENDLY NAME, NOT INTEGER
    # with_friendly = f"{last_def} = {friendly_name}"
    # lines[-1] = with_friendly
    # GET PINT UNIT
    matches = re.search(pint_first_def_regex, last_def)
    if not matches:
      raise ValueError
    groups = matches.groupdict()
    last_def_name = groups['name']
    for line in lines:
      # register module-level definition
      try:
        # not an alias - define unit
        if not groups['alias']:
          ureg.define(line)
      except pint.DefinitionSyntaxError as e:
        raise e
    # return tuple if unit, else nothing. index will be integer if unit
    if unit:
      try:
        unit = getattr(ureg, last_def_name)
      except pint.UndefinedUnitError as e:
        raise e
      return unit
  return None

# for tunerpro Unknown/Undefined/External/None to Python None - cast all to None, for Enum alias
NullOptions: ChainMap[int, t.Tuple[str, None]] = xml_type_map(
  'null_option',
  val = lambda el: (friendly_schemadef_name(el), None)
)
Prefixes: ChainMap[int, t.Tuple[str, None]] = xml_type_map(
  'unitPrefix',
  val = lambda el: (friendly_schemadef_name(el), pintify(el, unit=False))
)
# really, only these two are used
Measurements: ChainMap[int, str] = xml_type_map(
  'data',
  extends = [NullOptions]
)
Units: ChainMap[int, UnitDef] = xml_type_map(
  'unit',
  val = lambda el: UnitDef(
    friendly_name=friendly_schemadef_name(el), 
    unit = pintify(el)
  ),
  extends = [NullOptions]
)

# TODO - subclass pint.Quantity for custom stuff, like np.putmask?
Quantity = pint.Quantity
ArrayLike = t.Union[Quantity, Array]

class QuantityMixin(Base):
  '''
  Provides `data_type` and `unit_type` properties, e.g. vehicle speed in kilometers per second.
  '''
  @property
  def data_type(self) -> t.Optional[str]:
    '''
    E.g. Engine Speed, Exhaust Temp, Fuel Trim.
    '''
    index = int(self.xpath('./datatype/text()')[0])
    return Measurements[index]

  @property
  def unit(self) -> t.Optional[pint.Unit]:
    '''
    E.g. RPM, Quarts, Seconds, Percent, etc.
    '''
    index = int(self.xpath('./unittype/text()')[0])
    definition = Units[index]
    if definition[1] is not None:
      return Units[index].unit # type: ignore
    else:
      return None

FormatOutput: ChainMap[int, str] = xml_type_map(
  'formatting_output'
)

class FormattingMixin(Base):
  '''
  Provides:
    - `units` string
      * different from typed enumeration of units/measurements in `QuantityMixin`.
        For example, `Table.ZAxis` has `units` string, but not typed `QuantityMixin.data_type` or `QuantityMixin.unit_type`.
    - `output_type`
      * float, int, hex, or ASCII string.
  '''
  @property
  def units(self) -> t.Optional[str]:
    out = self.xpath('./units/text()')
    return out if out else None

  # TODO - use some sort of numpy memmap type?
  @property
  def output_type(self) -> str:
    out = self.xpath('./outputtype/text()')
    # if no XML element exists, default to float. `Table.XAxis`, `Table.YAxis`, `Constant` all do this.
    return FormatOutput[(int(out))] if out else FormatOutput[1]

  DEFAULT_DIGITS = 2

  @property
  def digits(self) -> int:
    '''
    When output type is floating point, this is the number of significant digits. 
    When integer, this is number of digits to truncate by.

    If no XML element, there is a default:
      - `Table.XYAxis` - 2
      - 'Table.ZAxis` - XML element always present, but default is 2
      - `Constant` - 2
      - `Function` - 2
    '''
    out = self.xpath('./decimalpl/text()')
    return int(out) if out else self.DEFAULT_DIGITS

