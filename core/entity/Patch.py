from __future__ import annotations
import typing as t
from .Base import Base, XdfRefMixin
from .Parameter import Parameter
from .EmbeddedData import print_array
import numpy as np
import numpy.typing as npt

class PatchEntry(Base, XdfRefMixin):
  '''
  Patches can have many entries, each of which is responsible
  for overwrting a section of binary data.
  '''
  name = Base.xpath_synonym('./@name')

  @property
  def address(self) -> int:
    return int(self.attrib['address'], 16)

  @property
  def size(self) -> int:
    '''
    Size in bytes. Patches must be in even sizes of 2 bytes
    '''
    return int(self.attrib['datasize'], 16)

  @property
  def patch(self):
    '''
    Hex-format string describing the data to overwrite. 
    TunerPro replaces any non-hex gibberish with "00" in its editor, e.g.
    
    DE AD BE EF gh gh g -> DE AD BE EF 00 00 0
    
    '''
    hex_str = self.xpath('./@patchdata')[0]
    chars = np.array([c for c in hex_str])
    words = np.array_split(chars, self.size)
    # intrinstic memmap data type is uint8
    return 

  # see `EmbeddedData`.memory_map
  @property
  def memory_map(self) -> np.memmap:
    return np.memmap(
      self._xdf._binfile,
      shape = (self.size, ),
      # TODO - account for XDF header base offset?
      offset = self.address,
      mode = 'w+'
      # by default, reads as uint8
    )
   
  @property
  def map_hex(self) -> npt.NDArray[np.unicode_]:
    return print_array(self.memory_map, hex) # type: ignore


class Patch(Parameter):
  '''
  XDF Patch - togglable overwriting of binary words.
  This parameter provides an explicit comparison to another binfile in to show
  whether or not it has been patched.
  '''
  entries: t.List[PatchEntry] = Base.xpath_synonym('./XDFPATCHENTRY', many=True)

  

__all__ = ['Patch', 'PatchEntry']  