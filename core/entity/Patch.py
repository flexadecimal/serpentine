from __future__ import annotations
import typing as t
from .Base import Base, XdfRefMixin
from .Parameter import Parameter
from .EmbeddedData import print_array, hex_to_array
import numpy as np
import numpy.typing as npt
import itertools as it

class UnpatchableError(ValueError):
  '''
  Raised when trying to unpatch an entry for which there is no original data to use.
  AKA "Indeterminate" status in TunerPro.
  '''
  entry: PatchEntry
  patch: Patch

  def __init__(self, entry: PatchEntry):
    self.entry = entry
    self.patch = entry.getparent()
    
  def __str__(self):
    root = self.entry.getroottree()
    path = root.getpath(self.entry)
    return f"""{repr(self.entry)} of {repr(self.patch)} at {path} has no basedata to undo the patch."""

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
  def patch(self) -> npt.NDArray[np.uint8]:
    '''
    Hex-format string describing the data to overwrite. 
    TunerPro replaces any non-hex gibberish with "00" in its editor, e.g.
    
    DE AD BE EF gh gh g -> DE AD BE EF 00 00 0
    
    '''
    hex_str = self.xpath('./@patchdata')[0]
    #. e.g. ['D' 'E' 'A' 'D' 'B' 'E' 'E' 'F']
    return hex_to_array(hex_str, self.size)

  @property
  def original(self) -> t.Optional[npt.NDArray[np.uint8]]:
    hex_str_query = self.xpath('./@basedata')
    hex_str = hex_str_query[0] if len(hex_str_query) > 0 else None
    return hex_to_array(hex_str, self.size) if hex_str else None

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
  def applied(self) -> bool:
    '''
    Indicates whether or not the patch data matches what's in the binary.
    '''
    return np.array_equal(self.patch, self.memory_map)

  def apply(self):
    '''
    Applies the patch to the specifed map data.
    '''
    self.memory_map[:] = self.patch[:]
    # TODO: FlushPool mixin?
    self.memory_map.flush()
    pass
  
  def remove(self):
    '''
    Remove the patch. Requires original data.
    '''
    if self.original is None:
      raise UnpatchableError(self)
    self.memory_map[:] = self.original[:]
    self.memory_map.flush()
  
  def __repr__(self):
    return f"<{self.__class__.__qualname__} '{self.name}'>"

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

  def apply_all(self):
    '''
    Apply all patches.
    '''
    for entry in self.entries:
      entry.apply()

  def remove_all(self):
    '''
    Remove all patches.
    '''
    for entry in self.entries:
      entry.remove()

  @property
  def applied(self):
    return all(map(lambda e: e.applied, self.entries))
  