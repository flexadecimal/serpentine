from re import M
import typing as t
import numpy.typing as npt
# for entities
from .Base import ArrayLike, Base, XdfRefMixin, Array, Quantity
# general stuff
import functools as ft
import numpy as np
from enum import Flag
import itertools as it
from .Math import Math
import pint

class TypeFlags(Flag):
  '''
  Type flags found in binary conversion - endianness, signed, etc.
  TunerPro uses "LSB first" (little-endian) and "MSB first" (big-endian)
  terminology.
  '''
  SIGNED = 1
  LITTLE_ENDIAN = 2
  FLOAT = 65536
  COLUMN_MAJOR = 4

class EmbeddedData(Base):
  '''
  Used under Math elements, providing details on parsing internal binary data.
  '''
  @property
  def address(self) -> t.Optional[int]:
    if 'mmedaddress' in self.attrib:
      return int(self.attrib['mmedaddress'], 16)
    else:
      return None
  
  @property
  def length(self) -> int:
    '''
    Length of binary data in bytes.
    '''
    return int(self.attrib['mmedelementsizebits']) // 8

  @property
  def shape(self) -> t.Union[t.Tuple[int], t.Tuple[int, int]]:
    '''
    Shape tuple following Numpy convention - 2D tables like that of `Table.ZAxis` have shape like `(16, 16)` (or occasionally `(16, )` for a 1D table). Constants have shape `(1, )` - a single number that will be broadcoast to an array length 1.
    '''
    if 'mmedrowcount' in self.attrib and 'mmedcolcount' in self.attrib:
      return (int(self.attrib['mmedrowcount']), int(self.attrib['mmedcolcount']))
    elif 'mmedcolcount' in self.attrib:
      return (int(self.attrib['mmedcolcount']), )
    elif 'mmedrowcount' in self.attrib:
      return (int(self.attrib['mmedrowcount']), )
    # this is a Constant
    else:
      return (1, )

  @property
  def type_flags(self) -> TypeFlags:
    if 'mmedtypeflags' in self.attrib:
      return TypeFlags(int(self.attrib['mmedtypeflags'], 16))
    else:
      return TypeFlags(0)
    
  @property
  def data_type(self) -> npt.DTypeLike:
    if TypeFlags.FLOAT in self.type_flags:
      type = 'f'
    elif TypeFlags.SIGNED in self.type_flags:
      type = 'i'
    else:
      type = 'u'
    endianness = '<' if TypeFlags.LITTLE_ENDIAN in self.type_flags else '>'
    type_str = f'{endianness}{type}{self.length}'
    return np.dtype(type_str)

  # table only
  @property
  def strides(self) -> t.Optional[t.Union[t.Tuple[int], t.Tuple[int, int]]]:
    '''
    Array stride in memory.
    '''
    major = int(self.attrib['mmedmajorstridebits']) // 8
    minor = int(self.attrib['mmedminorstridebits']) // 8
    if len(self.shape) == 2:
      return None if major == 0 and minor == 0 else (major, minor)
    elif len(self.shape) == 1:
      return None if major == 0 else (major, )
    else:
      raise ValueError

def print_array(
  x: ArrayLike, 
  printer: t.Callable[[t.Any], str] = str
) -> npt.NDArray[np.unicode_]:
  out = np.vectorize(printer)(x)
  # fill mask with default
  if np.ma.is_masked(out):
    out = out.filled('--')
  return out

def pad_with(vector, pad_width, iaxis, kwargs):
  '''
  Numpy padding utility function. See https://numpy.org/doc/stable/reference/generated/numpy.pad.html.
  '''
  pad_value = '  '
  vector[:pad_width[0]] = pad_value
  vector[-pad_width[1]:] = pad_value

def print_cols(kwargs: t.Mapping[str, ArrayLike]) -> str:  
  vals = kwargs.values()
  max_height = max(map(lambda x: np.array(x).shape[-1:], vals))[0]
  middle = max_height // 2
  as_char_arrays = {
    key: print_array(arr) for key, arr in kwargs.items()
  }
  def padder(key, arr):
    out = np.empty(arr.shape, dtype=np.unicode_)
    edge = max(middle, max_height)
    if len(arr.shape) == 1:
      out = np.pad([arr], (edge, edge), pad_with)[1: edge + 1]
    else:
      out = arr
    return out
  padded = {
    key: padder(key, arr) for key, arr in as_char_arrays.items()
  }
  combined = np.hstack(padded.values()) # type: ignore
  lines = list(map(
    lambda row: ''.join(row),
    combined
  ))
  out = '\n'.join(lines)
  return out

class EmbeddedValueError(ValueError):
  '''
  `raise`d when writing a value to a `memmap`-backed array would go outside of its intrinsic bounds and silently clip.

  TunerPro and `np.memmap` silently clip, but the editor needs to be shown logical/memmap bounds when editing. 
  '''
  min: npt.NDArray
  max: npt.NDArray
  val: npt.NDArray
  # used by callers to prompt user to correct only certain values
  out_minmax: t.Tuple[np.ma.masked_array, np.ma.masked_array]

  def __init__(self, min: npt.NDArray, max: npt.NDArray, val: npt.NDArray):
    self.min, self.max = min, max
    self.val = val
    # out of bounds values
    out_min: np.ma.masked_array = np.ma.masked_array(
      self.val, 
      mask = np.logical_not(self.val < self.min)
    )
    out_max: np.ma.masked_array = np.ma.masked_array(
      self.val, 
      mask = np.logical_not(self.val > self.max )
    )
    self.out_minmax = out_min, out_max
    pass
  
  def __str__(self):
    minmax_count = list(map(
      lambda bound: np.count_nonzero(bound.compressed()),
      self.out_minmax
    ))
    min, max = minmax_count
    out_min = print_cols({
      'invalid': self.out_minmax[0], 
      '': ['<'], 
      'min': self.min
    })
    out_max = print_cols({
      'invalid': self.out_minmax[1], 
      '': ['>'], 
      'max': self.max
    })
    # final adjustments
    out = ''
    out_minmax = '\n'.join([out_min, out_max])
    # set up print args
    # out on both bounds
    if min > 0 and max > 0:
      out = out_minmax
    # out on max only
    elif max > 0:
      out = out_max
    # out on min only
    else:
      out = out_min
    # print helpful info
    formatted = f"""Writing out-of-bounds values to memory map.

{out}
    """
    return formatted

class Embedded(XdfRefMixin):
  '''
  Mixin for objects exposing a value using both `<MATH>` and `<EMBEDDEDDATA>`.
  `Constant` and `Table.Axis` do this. `Table` has a value itself, but its value is constructed from "real" `Embedded` memory maps.
  '''
  EmbeddedData: EmbeddedData = Base.xpath_synonym('./EMBEDDEDDATA')
  Math: Math = Base.xpath_synonym('./MATH')

  @property
  def value(self) -> ArrayLike:
    unitless = self.Math.conversion_func(
      self.memory_map.astype(np.float_, copy=False)
    )
    return unitless

  @property
  def logical_bounds(self):
    '''
    Logical bounds of this value by its `numpy` data type, to raise `EmbeddedValueError` with and draw UI with
    '''
    min, max = map(
      self.Math.conversion_func,
      self.memmap_bounds
    )
    return min, max

  @value.setter # type: ignore
  def value(self, value): 
    matrix = np.array([value])
    min, max = self.logical_bounds
    out = self.Math.inverse_conversion_func(matrix)
    if Embedded.out_of_bounds(matrix, min, max):
      e = EmbeddedValueError(min, max, matrix)
      raise e
    else:
      # silently fail, write to map
      # see https://numpy.org/devdocs/reference/generated/numpy.memmap.html
      # this will implicitly truncate floats
      self.memory_map[:] = np.array([out])[:]
      # flush ? 
      #self.memory_map.flush()

  def clip_to_memmap_bounds(self, x: ArrayLike):
    min, max = self.memmap_bounds
    return np.clip(x, min, max)

  @staticmethod
  def out_of_bounds(x: npt.NDArray, real_min: npt.NDArray, real_max: npt.NDArray) -> bool:
    return bool(np.any(x > real_max) or np.any(x < real_min))

  @property
  def memmap_bounds(self) -> t.Tuple[npt.NDArray, npt.NDArray]:
    '''
    When writing back 'real' data to memory, there is a "max" value that can be converted back as a practical bound, e.g.
    [int] -> [255] * byte_width
    [float] -> [1]
    '''
    dtype_bounds = np.iinfo(self.EmbeddedData.data_type)
    min = np.full(self.EmbeddedData.shape, dtype_bounds.min)
    max = np.full(self.EmbeddedData.shape, dtype_bounds.max)
    return min, max
  
  @ft.cached_property
  def memory_map(self) -> np.memmap:
    embedded_data = self.EmbeddedData
    map: np.memmap = np.memmap(
      self._xdf._binfile,
      shape = embedded_data.shape,
      # see TunerPro docs - base offset not applied here
      offset = embedded_data.address,
      dtype = embedded_data.data_type,
      # 'C' for C-style row-major, 'F' for Fortran-style col major 
      order = 'F' if TypeFlags.COLUMN_MAJOR in embedded_data.type_flags else 'C',
      # enable write - `value` setters must explicitly flush
      mode='w+'
    )
    # set strides, if they exist - default XML stride of (0,0) is invalid
    if embedded_data.strides:
      map.strides = embedded_data.strides
    return map
    
  @property
  def map_hex(self) -> npt.NDArray[np.unicode_]:
    return print_array(self.memory_map, hex)