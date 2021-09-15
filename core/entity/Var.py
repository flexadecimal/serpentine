from abc import (
  ABC, abstractmethod
)
from .Base import Base, XmlAbstractBaseMeta, XdfRefMixin
from .Parameter import Parameter
import numpy as np
import numpy.typing as npt

class Var(Base):

  id: str = Base.xpath_synonym('./@id')
  
  def __repr__(self):
    return f"<{self.__class__.__qualname__} '{self.id}'>"
  

# this gets binary processing context, typically referred to as 'X' - a real class
class BoundVar(Var):
  pass

# linked vars and binary-reading vars inherit this - they are references in 
# binary context. this is just a logical stub
class FreeVar(Var, ABC, XdfRefMixin, metaclass=XmlAbstractBaseMeta):
  '''
  XDF paraemeters parse "their" section of the binary file - this is the bound variable. 
  Free variables are other already-calculated parameters or raw binary references. They need a reference to the contaning XDF to deliver values for `Math` function binding.

  https://en.wikipedia.org/wiki/Free_variables_and_bound_variables
  '''  
  @abstractmethod
  def value(self) -> npt.NDArray:
    pass
  
# actual tunerpro-style implementations
class LinkedVar(FreeVar):
  '''
  Links are references to already-calculated values, i.e. those before
  itself in the eval order (topsort of dependency graph).
  '''
  link_id = Base.xpath_synonym('./@linkid')

  @property
  def value(self) -> npt.NDArray:
    # TODO: this does NOT guard against circular references, neither does TunerPro. We need to guard against circular references when saving.
    # only Z-axis of Table used for value
    linked_param: Parameter = self.xpath(f"""
      //XDFTABLE[@uniqueid='{self.link_id}']/XDFAXIS[@id='z'] |
      //XDFCONSTANT[@uniqueid='{self.link_id}']
    """)[0]
    return linked_param.value
  
class AddressVar(FreeVar):
  '''
  Reference to raw binary data with toggles for endianness and bit length.
  This is similar to BoundVar context, but with global binary file scope and options belonging to the Var instance.
  '''
  @property
  def address(self) -> int:
    return int(self.xpath('./@address')[0], 16)
  
  @property
  def flags(self) -> int:
    return int(self.xpath('./@flags')[0], 16)

  @property
  def value(self) -> npt.NDArray:
    return np.memmap(
      self._xdf._binfile,
      shape = (1, ),
      offset = self.address,
      dtype = np.uint8
    )