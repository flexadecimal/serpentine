from __future__ import annotations
import typing as t
from .EmbeddedData import Embedded
from .Parameter import Parameter
from .EmbeddedData import TypeFlags, hex_to_array
import numpy as np
import numpy.typing as npt
import functools as ft

class Flag(Embedded, Parameter):
  '''
  Flag, a.k.a bitmask. In one byte, there are 8 possible locations for a bitmask.
  '''
  def __repr__(self):
    val = self.memory_map[0]
    return f"{Parameter.__repr__(self)}: {bin(val)}"

  def from_embedded(self, x: npt.NDArray):
    '''
    Identity converter for Flag that exposes the underlying memory map.
    '''
    return x

  def to_embedded(self, x: npt.NDArray):
    return x

  @property
  def mask(self) -> npt.NDArray[np.uint8]:
    ''' 
    Binary mask of array, e.g.
    0x8000 -> [1 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0]
    
    This should be set using bit selection, like TunerPro.
    '''
    hex_str = self.xpath('./mask/text()')[0]
    bytes = hex_to_array(hex_str, self.EmbeddedData.length)
    binary = np.unpackbits(bytes)
    return binary

  @property
  def value(self) -> bool:
    mask = self.mask
    binary_map = np.unpackbits(self.memory_map)
    masked = np.ma.masked_array(
      data = binary_map,
      mask = np.logical_not(mask)
    )
    first = masked.compressed()[0]
    return first == 1

  @value.setter
  def value(self, value: bool):
    mask = self.mask
    binary_map = np.unpackbits(self.memory_map)
    masked = np.ma.masked_array(
      data = binary_map,
      mask = np.logical_not(mask)
    )
    new = np.array(masked, copy=True)
    # see https://numpy.org/doc/stable/reference/generated/numpy.ma.flatnotmasked_contiguous.html
    slice = np.ma.flatnotmasked_contiguous(masked)[0]
    # overwrite
    new[slice] = 1 if value else 0
    # back into bytes
    new_bytes = np.packbits(new)
    self.memory_map[:] = new_bytes[:]
    # TODO: flushpool?
    self.memory_map.flush()
    return


  @ft.cached_property
  def memory_map(self) -> np.memmap:
    embedded_data = self.EmbeddedData
    # intrinsic dtype is np.uint8 - we want an array of individual bytes to join later
    orig_t = embedded_data.data_type
    uint8_arr = np.dtype(f"{orig_t.byteorder}u1") # type: ignore
    map = np.memmap(
      self._xdf._binfile,
      # we want an array of uint8 bytes this long
      shape = embedded_data.length,
      # see TunerPro docs - base offset not applied here
      offset = embedded_data.address if embedded_data.address else 0,
      # we always use intrinsic np.uint8, so we can have the collection of bytes
      dtype = uint8_arr,
      order = 'F' if TypeFlags.COLUMN_MAJOR in embedded_data.type_flags else 'C',
      mode='w+'
    )
    return map