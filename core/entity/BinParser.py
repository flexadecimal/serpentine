#import xml.etree.ElementTree as xml
from lxml import (
  etree as xml,
  objectify
)
import os, sys
import numpy as np
import pdb

from pathlib import Path
core_path = Path(__file__).parent.parent
schemata_path = os.path.join(core_path, 'schemata')
xdf_schema_path = 'xdf_schema.xsd'

from .Table import Table

class BinParser(object):
  '''
  Parses maps/signals (univariate signals like velocities, 3d surfaces like
  ignition maps) from the ECU ROM stored in the BIN file.
  TODO: provide interface to write changes from higher level signal logic
  '''
  def __init__(self, **kwargs):
    adx_tree = xml.parse(kwargs['adx'])
    # XDF
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
    parser = objectify.makeparser(schema = xdf_schema)
    xdf_object_tree = objectify.fromstring(xml.tostring(xdf_tree), parser)
    # map XDFTABLE object to our internal representation
    tables = list(map(
      lambda el: Table(
        header = xdf_object_tree.XDFHEADER,
        table = el,
        bin_file = kwargs['bin']
      ),
      list(xdf_object_tree.XDFTABLE)
    ))
    pdb.set_trace()
    
    constants = xdf_tree.xpath('/XDFFORMAT/XDFCONSTANT')
    # ...parse binary
    
    # xslt functional transformation
    
    # TODO: integrate into sql?
    