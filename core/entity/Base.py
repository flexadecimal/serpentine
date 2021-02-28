from sqlalchemy.orm import declared_attr
from sqlalchemy import (
  Column, Integer
)
import json

# see https://docs.sqlalchemy.org/en/14/orm/declarative_mixins.html
class Base(object):
  @declared_attr
  def __tablename__(cls):
    return cls.__name__.lower()
  
  # 'business logic' id - unique across all XDFs
  @declared_attr
  def id(cls):
    return Column(Integer, primary_key = True)
    
  def __repr__(self):
    internal = ['_sa_instance_state']
    filtered = {ley: val for key, val in vars(self).items() if key not in internal}
    return f'<class>{str(filtered)}'
      
  def toJSON(self):
    return json.dumps(self, default=lambda o: o.__dict__)