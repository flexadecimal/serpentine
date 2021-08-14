from typing import *
from .Base import Base, XmlAbstractBaseMeta, XdfRefMixin
from abc import ABC, abstractmethod
import functools
import numpy as np
import numpy.typing as npt
from enum import Flag

class TypeFlags(Flag):
  '''
  Type flags found in binary conversion - endianness, signed, etc.
  TunerPro uses "LSB first" (big-endian) and "MSB first" (little-endian)
  terminology.
  '''
  SIGNED = 1
  BIG_ENDIAN = 2
  FLOAT = 65536
  COLUMN_MAJOR = 4

class EmbeddedData(Base):
  '''
  Used under Math elements, providing details on parsing internal binary data.
  '''
  @property
  def address(self) -> Union[int, None]:
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
  def shape(self) -> Union[Tuple[int], Tuple[int, int]]:
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
    endianness = '>' if TypeFlags.BIG_ENDIAN in self.type_flags else '<'
    type_str = f'{endianness}{type}{self.length}'
    return np.dtype(type_str)

  # table only
  @property
  def strides(self) -> Union[Tuple[int], Tuple[int, int]]:
    '''
    Array stride in memory.
    '''
    major = int(self.attrib['mmedmajorstridebits']) // 8
    minor = int(self.attrib['mmedminorstridebits']) // 8
    if len(self.shape) == 2:
      return (major, minor)
    elif len(self.shape) == 1:
      return (major, )
    else:
      raise ValueError

class EmbeddedMathMixin(XdfRefMixin):
  '''
  Mixin for objects exposing a value using both `<MATH>` and `<EMBEDDEDDATA>`.
  `Constant` and `Table.Axis` do this. `Table` has a value itself, but its value is constructed from "real" `EmbeddedMathMixin` memory maps.
  '''
  EmbeddedData: EmbeddedData = Base.xpath_synonym('./EMBEDDEDDATA')

  @functools.cached_property
  def memory_map(self) -> npt.NDArray:
    embedded_data = self.EmbeddedData
    map: npt.NDArray = np.memmap(
      self._xdf._binfile,
      shape = embedded_data.shape,
      # see TunerPro docs - base offset not applied here
      offset = embedded_data.address,
      dtype = embedded_data.data_type,
      # 'C' for C-style row-major, 'F' for Fortran-style col major 
      order = 'F' if TypeFlags.COLUMN_MAJOR in embedded_data.type_flags else 'C',
    )
    # set strides
    map.strides = embedded_data.strides
    return map