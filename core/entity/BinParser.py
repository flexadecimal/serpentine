#import xml.etree.ElementTree as xml
from lxml import etree as xml
import os
import numpy as np
import pdb

from pathlib import Path
core_path = Path(__file__).parent.parent
schemata_path = os.path.join(core_path, 'schemata')

class BinParser(object):
  '''
  Parses maps/signals (univariate signals like velocities, 3d surfaces like
  ignition maps) from the ECU ROM stored in the BIN file.
  TODO: provide interface to write changes from higher level signal logic
  '''
  def __init__(self, **kwargs):
    adx_tree = xml.parse(kwargs['adx'])
    # ...get XDF schema
    xdf_schema = xml.XMLSchema(
      file = os.path.join(schemata_path, 'xdf_schema.xsd')
    )
    xdf_tree = xml.parse(kwargs['xdf'])
    # ...validate
    try:
      xdf_schema.validate(xdf_tree)
    except XMLSchemaParseError:
      pdb.set_trace()
    
    # ...get tables and constants
    #tables = xdf_tree.xpath('/XDFFORMAT/XDFTABLE')
    #constants = xdf_tree.xpath('/XDFFORMAT/XDFCONSTANT')
    
    
    # xslt functional transformation
    
    # TODO: integrate into sql?
    