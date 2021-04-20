from .common import *
# import parameter classes
from . import (
  Axis,
  Table
)
# for parsing math equations
from ..equation_parser import Equation

description_length = 5000
title_length = 100

# custom lookup for XDF XML types
# see https://lxml.de/element_classes.html#setting-up-a-class-lookup-scheme
class XdfTyper(xml.CustomElementClassLookup):
  
  xml_name_to_class = {
    #'XDFFORMAT': None,
    'XDFAXIS': Axis.Axis,
    'XDFTABLE': Table.Table,
  }
  
  def lookup(self, node_type, document, namespace, name):
    '''
    Custom class dispatcher for TunerPro XDF XML-based format.
    Dispatching is done by the `name` argument.
    '''
    if name in self.xml_name_to_class:
      klass = self.xml_name_to_class[name]
      return klass
    else:
      return None

class Xdf:
  def __init__(self, **kwargs):
    # ...get schema
    try:
      xdf_schema = xml.XMLSchema(
        file = os.path.join(schemata_path, xdf_schema_path)
      )
    except xml.XMLSchemaParseError as schema_error:
      print(f"<{type(self).__name__}>: Invalid schema '{xdf_schema_path}'.")
      print(schema_error)
      sys.exit()
    # ...validate
    xdf_tree = xml.parse(kwargs['xdf'])
    if not xdf_schema.validate(xdf_tree):
      print(f"<{type(self).__name__}>: XDF '{kwargs['xdf']}' not validated against schema '{xdf_schema_path}'.")
      print(xdf_schema.error_log)
      sys.exit()
    # ...objectify
    # xml-to-class parser
    parser = objectify.makeparser(schema = xdf_schema)
    parser.set_element_class_lookup(XdfTyper())
    xdf_object_tree = objectify.fromstring(xml.tostring(xdf_tree), parser)
    
    # map XDFTABLE object to our internal representation
    #self.header = xdf_object_tree.XDFHEADER
    #self.tables = list(xdf_object_tree.XDFTABLE)
    #self.constants = list(xdf_object_tree.XDFCONSTANT)
    # process equations into variable dependency tree via Lark
    #self.axes = list(xdf_object_tree.xpath('//XDFAXIS'))
    self.tables = list(xdf_object_tree.xpath('//XDFTABLE'))
    math_elements = xdf_object_tree.xpath('//MATH')
    ignition_map = list(self.tables[0])[0]
    #xml_print(self.axes[0])
    print(xml_print(ignition_map))
    #print(repr(ignition_map))
    x_axis = ignition_map.XDFAXIS[0]
    #data = x_axis.binary_data
    #math = x_axis.equation
    pdb.set_trace()
    
    