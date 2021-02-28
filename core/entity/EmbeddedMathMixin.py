from .common import *
from sqlalchemy.orm import declared_attr

max_equation_length = 1024

class XdfEmbeddedData(Base):
  '''
  Conversion factors for parsing signals from bins are stored here.
  Referenced by composite key (XDF id, feature UniqueId)
  - <XDFTABLE> -> <XDFAXIS UniqueId>
  - <XDFTABLE> -> <XDFCONSTANT UniqueId>
  '''

class EmbeddedMathMixin(object):
  '''
  Encapsulates the functionality in common between Constant and Axis - the
  parsing of math parameters from ECU .BIN files.
  '''
  # BIN PARSING PARAMETERS
  @declared_attr
  def mem_address(cls):
    return Column(Integer)
  
  @declared_attr
  def mem_bit_length(cls):
    return Column(Integer)
  
  @declared_attr
  def mem_major_stride_bits(cls):
    return Column(Integer)
  
  @declared_attr
  def mem_minor_stride_bits(cls):
    return Column(Integer)
    
  # TODO - figure out what DALINK does
  @declared_attr
  def da_index(cls):
    return Column(Integer)
  
  # PARSED MATH
  # in XML, var is a nested tag - flatten this here
  # TODO - maybe move this out to Math relation or special Math class?
  def equation(cls):
    return Column(String(max_equation_length))
    
  def decimal_places(cls):
    return Column(Integer)
  
  # Constant seems to always have this, Axis may not?
  def data_type(cls):
    return Column(Integer)
  def unit_type(cls):
    return Column(Integer)