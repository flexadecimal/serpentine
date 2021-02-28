import sqlalchemy
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import scoped_session

# SET UP AND PROVIDE [session, meta, engine] FOR CORE
server = 'sqlite:///test.db'
engine = sqlalchemy.create_engine(server, echo=True)
session_factory = sessionmaker()
session_factory.configure(bind=engine)
session = session_factory()
meta = sqlalchemy.schema.MetaData(bind=engine)

# IMPORT ENTITIES
from .entity import *
# ... a little hack - to avoid ugly namespaces like `User.User`, make an entity dict,
# e.g. entity['User'] = class User
entity = {klass: getattr(getattr(entity, klass), klass) for klass in entity.__all__}
__all__ = ['session', 'meta', 'engine', 'entity']