from lxml import (
  etree as xml,
  objectify,
)

import os, sys 
import numpy as np
import pdb
from pathlib import Path

from .Base import Base

core_path = Path(__file__).parent.parent
schemata_path = os.path.join(core_path, 'schemata')
xdf_schema_path = 'xdf_schema.xsd'

def xml_print(tree_list, chunk=2):
  #strings = list(map(
  #  lambda xml: objectify.dump(xml),
  #  filter(lambda xml: xml is not None, tree_list)
  #))
  #return '\n'.join(strings)
  return objectify.dump(tree_list)