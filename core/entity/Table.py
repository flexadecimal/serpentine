from .common import *
from .Parameter import Parameter
from .Axis import Axis

class Table(Parameter):
  '''
  Signal table, e.g. ignition map, boost control map, fuel map.
  '''
  __mapper_args__ = {
    'polymorphic_identity': 'table'
  }
  
  Axes = relationship(
    Axis,
    uselist = True
  )
  
  