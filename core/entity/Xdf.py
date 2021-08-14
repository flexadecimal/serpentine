from typing import *
from lxml import (
  etree as xml,
  objectify
)
import os
from pathlib import Path
# import parameter classes
from .Base import Base
from . import (
  Parameter, Table, Constant, 
  EmbeddedData, Math, Var
)
import graphlib
import functools

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
  title: str = Base.xpath_synonym('./XDFHEADER/deftitle/text()')
  description: str = Base.xpath_synonym('./XDFHEADER/description/text()')
  author: str = Base.xpath_synonym('./XDFHEADER/author/text()') 
  Categories = Base.xpath_synonym('./XDFHEADER/CATEGORY', many=True)
  Tables: List[Table.Table] = Base.xpath_synonym('./XDFTABLE', many=True)
  Constants: List[Constant.Constant] = Base.xpath_synonym('./XDFCONSTANT', many=True)
  # Tables and Constants are both Parameters, but Parameters have more general semantics in functions
  Parameters: List[Parameter.Parameter] = Base.xpath_synonym('./XDFTABLE | ./XDFCONSTANT', many=True)

  # internals
  @property
  def _bin_internals(self):
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
    xdf_object_tree: Xdf = objectify.fromstring(xml.tostring(xdf_tree), parser)    
    # ...set python special vars
    xdf_object_tree._binfile = open(binpath, 'r+b')
    return xdf_object_tree

  @property
  def parameters_by_id(self):
    return {param.id: param for param in self.Parameters}

  #graphlib topsort
  @functools.cached_property
  def math_eval_order(self) -> List[Math.Math]:
    has_link = self.xpath("//MATH[./VAR[@type='link']]")
    graph = {math:  
       #lambda id: self.xpath(f"//MATH[./VAR[@linkid='{id}']]")[0],
      list(map(lambda id: self.xpath(f"""
        //XDFTABLE[@uniqueid='{id}']/XDFAXIS[@id='z']/MATH | 
        //XDFCONSTANT[@uniqueid='{id}']/MATH
        """)[0],
        math.linked_ids.values()
      )) for math in has_link
    }
    try:
      sorter = graphlib.TopologicalSorter(graph)
      eval_order = list(sorter.static_order())
    except graphlib.CycleError as error:
      cycle = set(error.args[1])
      root = self.getroottree()
      paths = ', '.join(map(lambda p: f'{root.getpath(p)}', cycle))
      print(f"XDF cannot be evaluated - conversion equations {paths} are mutually interpendent.")
    return eval_order
    
# custom lookup for XDF XML types
# see https://lxml.de/element_classes.html#setting-up-a-class-lookup-scheme
class XdfTyper(xml.PythonElementClassLookup):
  name_to_class = {
    'XDFFORMAT': Xdf,
    'MATH': Math.Math,
    'XDFCONSTANT': Constant.Constant,
    'XDFTABLE': Table.Table,
    'EMBEDDEDDATA': EmbeddedData.EmbeddedData
  }
  
  # polymorphic dispatch by element
  @staticmethod
  def axis_polymorphic_dispatch(**attrib):
    if attrib['id'] == 'z':
      # special case for ZAxis - has many <MATH>, etc.
      return Table.ZAxis
    else:
      return Table.Axis

  @staticmethod
  def var_polymorphic_dispatch(**attrib):
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
  
  # dispatch attributes as arguments to functions. __func__ DOES exist on staticmethod, mypy doesn't know about this
  name_to_attrib_func = {
    'VAR': var_polymorphic_dispatch.__func__, #type: ignore
    'XDFAXIS': axis_polymorphic_dispatch.__func__, #type: ignore
  }
  
  def lookup(self, doc, root):
    '''
    Custom class dispatcher for TunerPro XDF XML-based format.
    '''
    if root.tag in self.name_to_attrib_func:
      func = self.name_to_attrib_func[root.tag]
      return func(**root.attrib)
    elif root.tag in self.name_to_class:
      klass = self.name_to_class[root.tag]
      return klass
    else:
      return None