from .common import *

name_length = 256

class Category(Base):
  name = Column(String(name_length))
  