from collections import ChainMap
from types import NoneType
import typing as t
from lxml import etree as xml, objectify
import os
from pathlib import Path
# import parameter classes
from .Base import Base
from . import (
  Parameter, Table, Constant, EmbeddedData, Var, Math, Axis, Function, Category, Patch, Flag
)

# export these errors for callers
Mathable = Axis.QuantifiedEmbeddedAxis | Table.ZAxis | Constant.Constant
UnpatchableError = Patch.UnpatchableError
EmbeddedValueError = EmbeddedData.EmbeddedValueError
CellEquationCalculationError = Axis.CellEquationCalculationError
# ... and allow these to be suppressed - mypy needs explicit `TypeAlias`
# see https://mypy.readthedocs.io/en/stable/common_issues.html#variables-vs-type-aliases
Ignorable: t.TypeAlias = EmbeddedData.EmbeddedValueError | Math.MathInterdependence | Axis.AxisInterdependence | Axis.CellEquationCalculationError

# this is import-time
core_path = Path(__file__).parent.parent
schemata_path = os.path.join(core_path, 'schemata')
xdf_schema_path = 'xdf_schema.xsd'
try:  
  xdf_schema = xml.XMLSchema(
    file = os.path.join(schemata_path, xdf_schema_path)
  )
except xml.XMLSchemaParseError as schema_error:
  print(f"XDF: Invalid schema '{xdf_schema_path}'.")
  raise schema_error

class Xdf(Base):
  # internals
  _path: Path
  _binfile: t.BinaryIO
  # public
  title: str = Base.xpath_synonym('./XDFHEADER/deftitle/text()')
  description: str = Base.xpath_synonym('./XDFHEADER/description/text()')
  author: str = Base.xpath_synonym('./XDFHEADER/author/text()') 
  Categories: t.List[Category.Category] = Base.xpath_synonym('./XDFHEADER/CATEGORY', many=True)
  Tables: t.List[Table.Table] = Base.xpath_synonym('./XDFTABLE', many=True)
  Constants: t.List[Constant.Constant] = Base.xpath_synonym('./XDFCONSTANT', many=True)
  Functions: t.List[Function.Function] = Base.xpath_synonym('./XDFFUNCTION', many=True)
  Patches: t.List[Patch.Patch] = Base.xpath_synonym('./XDFPATCH', many=True)
  Flags: t.List[Flag.Flag] = Base.xpath_synonym('./XDFFLAG', many=True)
  # Tables and Constants are both Parameters, but Parameters have more general semantics in functions
  Parameters: t.List[Parameter.Parameter] = Base.xpath_synonym(
    './XDFTABLE | ./XDFCONSTANT | ./XDFFUNCTION | ./XDFPATCH | ./XDFFLAG', 
    many=True
  )

  # TODO: type this
  @property
  def _bin_internals(self) -> t.Dict[str, t.Any]:
    '''
    Internal binary details - base offset, start address. Parameters use this to convert from binary to numerical data.
    '''
    out = dict(self.xpath('./XDFHEADER/REGION')[0].attrib)
    # cast and replace hex literals
    out['size'] = int(out['size'], base = 16)
    # base offset belongs here
    base_offset_attr = self.xpath('./XDFHEADER/BASEOFFSET')[0].attrib
    magnitude = int(base_offset_attr['offset'], 16)
    base_offset = -magnitude if bool(int(base_offset_attr['subtract'])) else magnitude
    out['base_offset'] = base_offset
    return out

  @classmethod
  def from_path(
    cls, 
    path: Path, 
    binpath: Path, 
    *ignore: t.Iterable[Ignorable]
  ):
    # ...validate
    #xdf_tree = xml.fromstring(string)
    xdf_tree = xml.parse(path)
    try:
      xdf_schema.assertValid(xdf_tree)
    except xml.DocumentInvalid as error:
      print(f"XDF '{path}' not validated against schema '{xdf_schema_path}'.")
      raise error
    # ...objectify - bind classes
    parser = objectify.makeparser(schema = xdf_schema)
    # TODO: singleton XdfTyper
    parser.set_element_class_lookup(XdfTyper())
    xdf: Xdf = objectify.fromstring(xml.tostring(xdf_tree), parser)    
    # ...set python special vars
    xdf._path = Path(path)
    xdf._binfile = open(binpath, 'r+b')
    # SANITY CHECKS 
    # - check cyclical references, ignoring those specified. you may want to ignore acyclic references to open edit-only UI and prompt user to fix it.
    # - multiple "CELL" funcs with precalc=False - this crashes TunerPro!
    try:
      # this must be fully evaluated to see if it is cyclical
      math_ok = Math.Math.acyclic(xdf)
      axes_ok = Axis.AxisLinked.acyclic(xdf)
      # check for cell funcs with multiple precalc=False, to prevent UB/crashes in original TunerPro
      all_math: t.Iterable[Math.Math] = xdf.xpath("//MATH")
      #counter = Axis.CellCounter()
      math_to_count = map(
        # counter.transform
        # new counter for each math
        lambda m: (m, Axis.CellCounter().transform(m.equation)),
        all_math
      )
      invalid = next(
        filter(
          lambda math_count: math_count[1] > 1,
          math_to_count
        ),
        None
      )
      if invalid is not None:
        bad_math = invalid[0]
        raise Axis.CellEquationCalculationError(xdf, bad_math)
      pass
    except Math.MathInterdependence as e:
      # TODO: math cleanup? mark invalid with special state?
      if Math.MathInterdependence not in ignore:
        raise(e)
    except Axis.AxisInterdependence as e:
      if Axis.AxisInterdependence not in ignore:
        raise(e)
    except Axis.CellEquationCalculationError as e:
      if Axis.CellEquationCalculationError not in ignore:
        raise(e)
    return xdf

  @property
  def parameters_by_id(self) -> t.Dict[str, Parameter.Parameter]:
    return {param.id: param for param in self.Parameters}

  def address(self, addr: int, bits: int, lsbfirst: bool, signed: bool):
    '''
    Returns raw value at address, offset by header base offset.
    '''
    return 0

  def this(self):
    '''
    Returns raw value (i.e. "accumulator" in our parlance) of the current object, or cell if Table or Axis.
    '''
    return 0

  def that(self, id: int, row: int, col: int, precalc: int):
    '''
    Returns value of another object, by decimal id (saved as hex string in XML `uniqueid` attribute)
    - If Table or Function, index by row and col.
    - if precalc, returns raw value, else calculated.
    '''
    return 0

  @property
  def _namespace(self):
    '''
    XDF object conversion functions available to equation editor namespace. 
    Things like `Axis`, `ZAxis`, `Constant` can call these functions by inheriting this namespace.
    '''
    return {
      'ADDRESS': self.address,
      'THIS': self.this,
      'THAT': self.that
    }

   
class ReadOnlyEmbeddedAxisMath(Axis.EmbeddedAxisMath):
  '''
  An `Axis` can be a Label Axis, and still have a <MATH> element under it.
  In TunerPro, this Math object is not editable until the Axis is switched to an EmbeddedAxis.

  LXML 'objectification' must return a class - specifically, a 
  subclass of `type` - `NoneType` would fit here, but it is not a subclass,
  so this class is used as a sentinel.
  '''
  # TODO: make all props read only?
  def _namespace(self):
    return ChainMap()


class XdfTyper(xml.PythonElementClassLookup):
  '''
  XML-to-XDF class dispatcher.
  See https://lxml.de/element_classes.html#setting-up-a-class-lookup-scheme.
  '''
  name_to_class = {
    'XDFFORMAT': Xdf,
    'CATEGORY': Category.Category,
    'MATH': Math.Math,
    'XDFCONSTANT': Constant.Constant,
    'XDFTABLE': Table.Table,
    'EMBEDDEDDATA': EmbeddedData.EmbeddedData,
    'XDFFUNCTION': Function.Function,
    'XDFPATCH': Patch.Patch,
    'XDFPATCHENTRY': Patch.PatchEntry,
    'XDFFLAG': Flag.Flag
  }
  
  # polymorphic dispatch by element
  @staticmethod
  def axis_polymorphic_dispatch(root, **attrib) -> t.Type[Axis.Axis]:
    id = attrib['id']
    parent = root.getparent().tag
    if parent == 'XDFTABLE':
      if id == 'z':
        return Table.ZAxis
      elif id == 'x' or id == 'y':
        klass = Axis.Axis_class_from_element(root)
        return klass
    elif parent == 'XDFFUNCTION':
      return Axis.FunctionAxis
    else:
      return Axis.Axis
    return Axis.Axis

  @staticmethod
  def var_polymorphic_dispatch(root, **attrib):
    type_to_class = {
      'link': Var.LinkedVar,
      'address': Var.AddressVar,
    }
    if 'type' in attrib:
      if attrib['type'] in type_to_class:
        klass = type_to_class[attrib['type']]
      else:
        raise NotImplementedError
    else:
      # implicit binary conversion variable, typically 'X'
      klass = Var.BoundVar
    return klass

  @staticmethod
  def math_polymorphic_dispatch(root, **attrib) -> t.Type[Math.Math]:
    parent = root.getparent()
    if parent.tag == "XDFAXIS":
      # is a Table ZAxis...
      if parent.attrib['id'] == 'z':
        if 'row' in attrib and 'col' in attrib:
          return Table.CellMath
        elif 'row' in attrib:
          return Table.RowMath
        elif 'col' in attrib:
          return Table.ColumnMath
        else:
          return Table.GlobalMath
      # is a regular X/Y Axis 
      else:
        parent_class = Axis.Axis_class_from_element(parent)
        # you can have <MATH> elements under Label Axes. 
        # TunerPro doesn't allow you to edit the Math when the Axis is set as Label,
        # so our data model should remove it/make None/otherwise exclude
        if parent_class is not Axis.XYEmbeddedAxis:
          return ReadOnlyEmbeddedAxisMath
        return Axis.EmbeddedAxisMath
    # constant has different Math, with no accumulator namespacing
    elif parent.tag == 'XDFCONSTANT':
      return Constant.ConstantMath
    else:
      raise NotImplementedError("Invalid parent for `<MATH>` element.")

  # dispatch attributes as arguments to functions. __func__ DOES exist on staticmethod, mypy doesn't know about this
  name_to_attrib_func = {
    'VAR': var_polymorphic_dispatch.__func__, #type: ignore
    'XDFAXIS': axis_polymorphic_dispatch.__func__, #type: ignore
    'MATH': math_polymorphic_dispatch.__func__ # type: ignore
  }
  
  def lookup(self, doc, root):
    '''
    Custom class dispatcher for TunerPro XDF XML-based format.
    '''
    if root.tag in self.name_to_attrib_func:
      func = self.name_to_attrib_func[root.tag]
      return func(root, **root.attrib)
    elif root.tag in self.name_to_class:
      klass = self.name_to_class[root.tag]
      return klass
    else:
      return None