from sqlalchemy.orm import declared_attr
from sqlalchemy import (
  Column, String, ForeignKey
)
from .Xdf import Xdf

class XdfIdMixin(object):
  col_length = 100
  '''
  Represented in XDF as hexadecimal id. Used by:
  - <XDFTABLE> -> <XDFAXIS>
  - <XDFCONSTANT>
  
  '''
  # TODO - custom type to read 
  @declared_attr
  def xdf_id(cls):
    return Column(String(XdfIdMixin.col_length), ForeignKey(Xdf.id))
  