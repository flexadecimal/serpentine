from .common import *
from .Category import Category

# don't circular import
#from .Parameter import Parameter

description_length = 5000
title_length = 100

class Xdf(Base):
  title = Column(String(title_length))
  
  Categories = relationship(
    Category,
    uselist = True
  )
  
  # load all parameters - Tables and Constants
  Parameters = relationship(
    'Parameter',
    uselist = True
  )
  
  