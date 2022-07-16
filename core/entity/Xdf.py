import typing as t
from lxml import etree as xml, objectify
import os
from pathlib import Path
# import parameter classes
from .Base import Base
from . import (
  Parameter, Table, Constant, EmbeddedData, Var, Math, Axis, Function, Category
)
import graphlib
import functools
from itertools import chain

Mathable = t.Union[Axis.QuantifiedEmbeddedAxis, Table.ZAxis, Constant.Constant]

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
  # Tables and Constants are both Parameters, but Parameters have more general semantics in functions
  Parameters: t.List[Parameter.Parameter] = Base.xpath_synonym(
    './XDFTABLE | ./XDFCONSTANT | ./XDFFUNCTION', 
    many=True
  )

  # internals
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
  def from_path(cls, path, binpath):
    # ...validate
    #xdf_tree = xml.fromstring(string)
    xdf_tree = xml.parse(path)
    try:
      xdf_schema.assertValid(xdf_tree)
    except xml.DocumentInvalid as error:
      print(f"XDF '{path}' not validated against schema '{xdf_schema_path}'.")
      # propogate error
      raise error
    # ...objectify - bind classes
    parser = objectify.makeparser(schema = xdf_schema)
    parser.set_element_class_lookup(XdfTyper())
    xdf: Xdf = objectify.fromstring(xml.tostring(xdf_tree), parser)    
    # ...set python special vars
    xdf._path = Path(path)
    xdf._binfile = open(binpath, 'r+b')
    # SANITY CHECK - interdependent conversion equations
    try:
      # this must be fully evaluated to see if it is cyclical
      order = list(xdf._math_eval_order)
    except graphlib.CycleError as error:
      cycle: t.Set[Math.Math] = set(error.args[1])
      # TODO: trying to construct kwargs of `Math.conversion_func` fails if they are dependent - YOU WILL OVERFLOW STACK. mark them dirty
      raise MathInterdependence(xdf, *cycle) from error
    # invalid state taken care of, we can still open
    return xdf

  @property
  def parameters_by_id(self) -> t.Dict[str, Parameter.Parameter]:
    return {param.id: param for param in self.Parameters}


  @functools.cached_property
  def _math_dependency_graph(self) -> t.Mapping[Math.Math, t.Iterable[Math.Math]]:
    has_link: t.Iterable[Math.Math] = self.xpath("//MATH[./VAR[@type='link']]")
    # see `Var.LinkedVar`
    #graph = {math:  
    #  list(map(lambda id: self.xpath(f"""
    #    //XDFTABLE[@uniqueid='{id}']/XDFAXIS[@id='z']/MATH | 
    #    //XDFCONSTANT[@uniqueid='{id}']/MATH
    #    """)[0],
    #    math.linked_ids.values()
    #  )) for math in has_link
    #}
    graph = {
      # TODO: flatten math 
      math: list(chain.from_iterable(var.linked.Math for var in math.LinkedVars))
      for math in has_link
    }
    return graph

  #graphlib topsort
  @property
  def _math_eval_order(self) -> t.Iterable[Math.Math]:
    graph = self._math_dependency_graph
    sorter = graphlib.TopologicalSorter(graph)
    return sorter.static_order()
    
class MathInterdependence(Exception):
  def __init__(self, root: Xdf, *interdependent_maths: Math.Math):
    self.cycle = interdependent_maths
    # fancy printing
    root_tree: xml.ElementTree = root.getroottree()
    printouts: t.List[str] = []
    for math in interdependent_maths:
      # var.linked.Math may be a list in case of `Table.ZAxis`, when you have many conversion equation masks
      linked_Maths = set(
        chain.from_iterable(var.linked.Math for var in math.LinkedVars)
      )
      dependent = next(iter(linked_Maths.intersection(interdependent_maths)))
      dependent_Var = next(filter(
        lambda var: dependent in var.linked.Math, math.LinkedVars
      ))
      # set printout
      printout = "  "
      printout += f"{root_tree.getpath(math.getparent())}: {math.attrib['equation']}"
      printout += f"\n    {dependent_Var.id}: {root_tree.getpath(dependent)}"
      printouts.append(printout)
      seperator = ',\n'
    message = f"""Parameter conversion equations in file `{root._path}`
    
{seperator.join(printouts)}

are mutually interdependent.
    """
    Exception.__init__(self, message)
 
# custom lookup for XDF XML types
# see https://lxml.de/element_classes.html#setting-up-a-class-lookup-scheme
class XdfTyper(xml.PythonElementClassLookup):
  name_to_class = {
    'XDFFORMAT': Xdf,
    'CATEGORY': Category.Category,
    'MATH': Math.Math,
    'XDFCONSTANT': Constant.Constant,
    'XDFTABLE': Table.Table,
    'EMBEDDEDDATA': EmbeddedData.EmbeddedData,
    'XDFFUNCTION': Function.Function
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
      return Axis.EmbeddedAxis
    else:
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
  def math_polymorphic_dispatch(root, **attrib) -> t.Type[Table.MaskedMath]:
    if 'row' in attrib and 'col' in attrib:
      return Table.CellMath
    elif 'row' in attrib:
      return Table.RowMath
    elif 'col' in attrib:
      return Table.ColumnMath
    else:
      return Table.GlobalMath

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