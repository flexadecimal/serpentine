from .common import *
from .EmbeddedMathMixin import EmbeddedMathMixin

name_length = 30

class Axis(Base, EmbeddedMathMixin):
  '''
  XDF tables contain multiple axes - they can be univariate, or 2D/3D surfaces.
  '''
  table_id = Column(Integer, ForeignKey('Table.id'))
  # XML: <XDFAXIS id='y'> 
  name = Column(String(name_length))
  #...math and bin parsing from EmbeddedMathMixin
  
  # units
  units = Column(String(30))
  min = Column(Numeric)
  max = Column(Numeric)
  
