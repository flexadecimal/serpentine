from __future__ import annotations
from lxml import (
  etree as xml,
  objectify,
)
import itertools as it
from abc import ABC
import functools
from typing import *

# to avoid circular import for XDF self-reference. __future__ import above for Xdf typehint
if TYPE_CHECKING:
  from .Xdf import Xdf

# need to do Union here for linter to be happy
xml_base = Union[xml.ElementBase]
#xml_base = objectify.ObjectifiedDataElement

class XmlClassMeta(type):
  
  @staticmethod
  def property_funcs(dikt, bases):
    base_descendant = it.takewhile(
      lambda base: base != xml_base,
      bases
    )
    # child dict union with inherited bases' dicts
    lineage_vars = functools.reduce(
      lambda a, b: a | b,
      map(lambda base: base.__dict__, base_descendant),
      dikt
    )
    property_funcs = list(filter(
      lambda key_val: type(key_val[1]) == property,
      lineage_vars.items()
    ))
    return property_funcs
  
  def __new__(cls, name, bases, dikt):
    new_dict = {}
    if __debug__:
      new_dict['__property_funcs__'] = XmlClassMeta.property_funcs(dikt, bases)
    
    klass = super().__new__(cls, name, bases, dikt | new_dict)
    return klass

class Base(xml_base, metaclass=XmlClassMeta):
  '''
  LXML ElementBase custom base class entities.
  TODO:
  - json serialization for API
  - read/write binding to XML structure
  '''
  @staticmethod
  def __xpath_dispatch(element, xpath_expression, many):
    result = element.xpath(xpath_expression)
    if len(result) == 0 and not many:
      return None
    elif len(result) == 1 and not many:
      return result[0]
    else:
      return result
  
  @classmethod
  def xpath_synonym(cls, xpath_expression, many = False, collection_class=dict):
    '''
    Type-generic binding to lxml element, e.g. Axes -> XDFAXIS
    '''
    return property(
      # getter
      lambda self: Base.__xpath_dispatch(self, xpath_expression, many),
      # setter
      lambda self, val: setattr(self, '', val)
      # deleter
      #lambda self, name: 
    )
  
  # custom init, see:
  # https://lxml.de/element_classes.html#setting-up-a-class-lookup-scheme
  # remember - self is an xml element, so has .xpath(), .attrib, etc.
  #def _init(self):
  #  if __debug__:
  #    # eager init @property's, so they can be shown in vars
  #    for name, val in self.__property_funcs__:
  #      self.__dict__[name] = val.__get__(self)
    
  def __str__(self):
    return objectify.dump(self)
  
  def __repr__(self):
    return self.getroottree().getpath(self)

class XmlAbstractBaseMeta(type(Base), type(ABC)): #type: ignore
  '''
  For Python class weirdness - see [this StackOverFlow answer](https://stackoverflow.com/a/61350480).
  Children of `Base` that are abstract must use this metaclass rather than `ABCMeta` directly, e.g.:
  ```
  Var(Base):
    @abstractmethod
    def foo()

  LinkedVar(Var, ABC, metaclass=XmlAbstractBaseMeta)
  ```
  '''
  pass

class XdfRefMixin:
  '''
  Utility Mixin class that provides the `_xdf` reference to the containing document.
  '''
  @property
  def _xdf(self: Any) -> Xdf:
    return self.xpath("/XDFFORMAT")[0]