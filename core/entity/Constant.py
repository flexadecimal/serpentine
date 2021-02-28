from .common import *
from .Parameter import Parameter
from .EmbeddedMathMixin import EmbeddedMathMixin

class Constant(EmbeddedMathMixin, Base):
  '''
  XDF constants describe the translation of engine tuning parameters from
  the binary ROMs of various ECUs.
  Constants and Axes share common interfaces:
    - EMBEDDEDDATA .bin parsing
    - MATH equation parsing
  '''
  #unique_id = 
  __mapper_args__ = {
    'polymorphic_identity': 'constant',
  }
  
  # ...math and embedded parsing from EmbeddedMathMixin
  
  # constant-specific data
  data_type = Column(Integer)
  unit_type = Column(Integer)