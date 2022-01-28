from .Base import Base, ArrayLike
from .Axis import XYEmbeddedAxis
from .Parameter import Parameter
import numpy as np
import pint

class Function(Parameter):
  '''
  XDF Function - an X <-> Y mapping. Very similar to Table, minus a third Z Axis. Apparently common in Ford applications.
  '''
  x: XYEmbeddedAxis = Base.xpath_synonym("./XDFAXIS[@id = 'x']")
  y: XYEmbeddedAxis = Base.xpath_synonym("./XDFAXIS[@id = 'y']")

  # when linked, refer to the y axis
  # TODO - maybe return function(x: Array) -> Array?
  @property
  def value(self) -> ArrayLike:
    return self.y.value
