import pdb
from struct import (
  pack, unpack
)
import numpy as np
from lark import Lark
from lark.indenter import Indenter
import os
from pathlib import Path

schemata_path = os.path.abspath(os.path.join(Path(__file__).parent.parent, 'schemata'))

math_grammar_path = os.path.join(schemata_path, 'tunerpro_math.lark')

# SEEK-BASED READ/WRITE INTERFACE TO BINARY FILE, BOUND WITH embedded_data ARGS
# essentially a closure, binds the embedded_data offset, stride, etc. to 
# file.seek and struct.pack/struct.unpack 
class BinaryBinder:
  def __init__(self, file, **kwargs):
    self.file = file
    # set params from xml attributes
    self.params = {
      'address': int(kwargs['mmedaddress'], 16),
      'width_in_bits': int(kwargs['mmedelementsizebits']),
      'num_columns': int(kwargs['mmedcolcount']),
      'major_stride': int(kwargs['mmedmajorstridebits']),
      'minor_stride': int(kwargs['mmedminorstridebits'])
    }
    self.axis = kwargs['axis']
  
  # as numpy array - used for all logic
  @property
  def read(self):
    # memory-map the array against the bin file
    data = np.memmap(
      self.file,
      dtype='uint8',
      mode='r',
      #shape = (self.params['major_stride'],),
      shape = (16,),
      offset = self.params['address']
    )
    # translate raw values to values scaled by equation
    scaled = data.astype(np.int)*30
    # TODO: move this to ScaledData interface
    equation = self.axis.MATH.attrib['equation']
    # parse math
    kwargs = dict(rel_to=__file__, start='file_input')
    parser = Lark.open(math_grammar_path, parser='lalr', **kwargs).parse
    # override
    equation = '(x+30+sin(30)+ROUND(2.0; 3) << 2) + IF(0xfe9 < 2; y; FALSE) + 2 ^ 6'
    try:
      print(f'{equation}')
      tree = parser(f'{equation}')
      print(tree.pretty())
      pdb.set_trace()
    except Exception as error:
      print(error)
      pdb.set_trace()
    # shape

  @property
  def as_bytes(self):
    # seek
    self.file.seek(self.params['address'])
    # read bytes
    
    pdb.set_trace()

class Table(object):
  def __init__(self, **kwargs):
    base_offset = kwargs['header'].baseoffset
    xdf_table = kwargs['table']
    # set table attributes
    self.title = xdf_table.title
    # parse each axis
    for axis in list(xdf_table.XDFAXIS):
      embedded_data = {key: val for key, val in axis.EMBEDDEDDATA.attrib.iteritems()}
      data_interface = BinaryBinder(
        kwargs['bin_file'],
        # extend embedded data
        **embedded_data,
        axis = axis
      )
      byte_digest = data_interface.read
      pdb.set_trace()
      pass