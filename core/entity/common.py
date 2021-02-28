# FOR ENTITY DEFINITIONS
from sqlalchemy.ext.declarative import declarative_base
# basic types
from sqlalchemy import (
  Column, Integer, String, DateTime, Numeric, ForeignKey, Table, Float
)
# relationship stuff
from sqlalchemy.orm import (
  relationship, backref, composite, foreign, remote
)

# FOR CORE
# ...session, meta, engine from core
from .. import session, meta, engine
# custom base with automatic tablenames, dev friendly repr, and automatic json serialization
from .Base import (
  Base as custom_base
)
Base = declarative_base(cls = custom_base, metadata = meta)

# MIXINS
# ...shared FK to single XDF
from .XdfIdMixin import XdfIdMixin
# ..too specific to include here
#from .EmbeddedMathMixin import EmbeddedMathMixin
