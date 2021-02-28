from .common import *
from .Category import Category
from sqlalchemy.orm import declared_attr
from .EmbeddedMathMixin import EmbeddedMathMixin

# would be nice if we had some sort of XDF XML schema definition to pull these from
description_length = 5000
title_length = 100
unique_id_length = 10

class Parameter(Base, XdfIdMixin):
  '''
  Base Parameter class. Table and Constant extend from this.
  '''
  title = Column(String(title_length))
  # seems to be HTML escaped
  # if null, no node in XML
  description = Column(String(description_length), nullable=True)
  # saved in XML as Parameter -> <CATEGORYMEM>
  Category = relationship(
    Category,
    uselist = True
  )
  # for polymorphism
  type = Column(String(50))
  
  __mapper_args__ = {
    'polymorphic_identity': 'parameter',
    'polymorphic_on': 'type'
  }