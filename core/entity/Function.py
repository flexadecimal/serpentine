from .Base import Base, ArrayLike
from .Math import Math
from .Axis import XYAxis
from .Parameter import Parameter
import numpy as np
import pint

class Function(Parameter):
  '''
  XDF Function - an X <-> Y mapping. Very similar to Table, minus a third Z Axis.
  '''
  x: XYAxis = Base.xpath_synonym("./XDFAXIS[@id = 'x']")
  y: XYAxis = Base.xpath_synonym("./XDFAXIS[@id = 'y']")

  # when linked, refer to the y axis
  # TODO - maybe return function(x: Array) -> Array?
  @property
  def value(self) -> ArrayLike:
    return self.y
