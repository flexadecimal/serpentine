from lxml import (
  etree as xml,
  objectify,
)
import inspect
import itertools as it
import functools
import pdb
from textwrap import(
  indent
)

xml_base = objectify.ObjectifiedDataElement

class XmlClassMeta(type):
  def __new__(cls, name, bases, dikt):
    # @property funcs declared - save so lxml _init can init them
    base_descendant = it.takewhile(
      lambda base: base != xml_base,
      bases
    )
    # child dict union with inherited bases' dicts
    everybody_vars = functools.reduce(
      lambda a, b: a | b,
      map(lambda base: base.__dict__, base_descendant),
      dikt
    )
    # so lxml _init can set them
    property_funcs = list(filter(
      lambda key_val: type(key_val[1]) == property,
      everybody_vars.items()
    ))
    # new in 3.9 - dict union. change to zip trick if you want
    new_dict = dikt | {
      '__property_funcs__': property_funcs
    }
    klass = super().__new__(cls, name, bases, new_dict)
    return klass

class Base(xml_base, metaclass=XmlClassMeta):
  '''
  LXML ElementBase custom base class entities.
  TOOD:
  - json serialization for API
  - read/write binding to XML structure
  '''
  # custom init, see:
  # https://lxml.de/element_classes.html#setting-up-a-class-lookup-scheme
  # remember - self is an xml element, so has .xpath(), .attrib, etc.
  def _init(self):
    # eager init @property's, so they can be shown in vars
    for name, val in self.__property_funcs__:
      self.__dict__[name] = val.__get__(self)
    
  def __repr__(self):
    return indent(
      f'{str(vars(self))}',
      #f'{type(self)}\n{str(vars(self))}',
      '\t'
    )