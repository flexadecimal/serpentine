from typing import *
from .Base import Base, XdfRefMixin
from .EmbeddedData import EmbeddedMathMixin
from .Parameter import Parameter
from .Math import Math, ConversionFuncType
import numpy as np
import numpy.typing as npt
import functools

class Axis(Base, EmbeddedMathMixin):
  Labels = Base.xpath_synonym('./LABEL', many=True)
  Math: Math = Base.xpath_synonym('./MATH')
  
  # each axis is a memory-mapped array
  @property
  def value(self) -> npt.NDArray:
    return self.Math.conversion_func(
      self.memory_map.astype(
        np.float64, 
        copy=False
        # use the underlying embedded row/col major ordering, shape, etc.
      )
    )

class ZAxis(Axis):
  '''
  Special-case axis, generally referred to interchangeably with as a "Table", although the Table really contains the Axes and their related information.

  Table Z axes may have multiple `<MATH>` conversion equations:
  - one global,
  - for each row,
  - for each column,
  - for each cell (row and column)

  ...in order from lowest to highest priority.
  '''
  global_Math: Math = Base.xpath_synonym('./MATH[not(@row) and not(@col)]')
  column_Math: Math = Base.xpath_synonym('./MATH[@col and not(@row)]', many=True)
  row_Math: Math = Base.xpath_synonym('./MATH[@row and not(@col)]', many=True)
  cell_Math: List[Math] = Base.xpath_synonym('./MATH[@row and @col]', many=True)

  @property
  def _equation_grid(self) -> List[List[ConversionFuncType]]:
    '''
    This is used internally for conversion - equations are replaced by priority.
    
    For example, with a global equation, row equation, and cell equation, the table is filled with the global, row, then cell equation so that the correct equation can then be looked up by row/column index.

    TunerPro represents an equation grid in the UI - this is related, but not that.
    '''
    # create initial table with global func. linter ignore because shape should be size 2, but can be Tuple[int] (size 1) when constant
    rows, cols = self.EmbeddedData.shape # type: ignore
    out = [
      [self.global_Math.conversion_func for row in range(rows)]
      for col in range(cols)
    ]    
    # ...overwrite row...
    for math in self.column_Math:
      for n in range(rows):
        out[n][int(math.attrib['col']) - 1] = math.conversion_func
    # ...then column...
    for math in self.row_Math:
      for n in range(cols):
        out[int(math.attrib['row']) - 1][n] = math.conversion_func
    # ...then cell funcs
    for math in self.cell_Math:
      row, col = int(math.attrib['row']) - 1, int(math.attrib['col']) - 1
      out[row][col] = math.conversion_func
    return out

  # TODO - refactor this in non-iterative way? this is expensive
  #@property
  @functools.cached_property
  def value(self) -> npt.NDArray:
    #for row in eq_grid:
    #  for f in row:
    #    print(f.__doc__, end='  ')
    #  print()
    eq_grid = self._equation_grid
    # apply matching functions over copy
    copy = np.empty(self.memory_map.shape)
    for x ,y in np.ndindex(copy.shape): # type: ignore
      copy[x][y] = eq_grid[x][y](self.memory_map[x][y])
    return copy


class Table(Parameter):

  @property
  def Axes(self) -> dict[str, Axis]:
    '''
    3D surface with X, Y, and Z axes.
    '''
    return {axis.attrib['id']: axis for axis in self.xpath('./XDFAXIS')}

  @property
  def value(self):
    return self.Axes['z'].value

  def __str__(self):
    sep = ' '
    width = 6
    fmt = f"{{0:>{width}.1f}}"
    x_axis = sep.join(map(
      lambda x: fmt.format(x), self.Axes['x'].value
    ))
    x_preceding = ' ' * (width + 2 + len(sep))
    line = '-' * len(x_axis) 
    # prepend y value for each z-axis table row
    zs_with_y = '\n'.join(
      sep.join([
        # preceding y val
        fmt.format(self.Axes['y'].value[index]),
        # divider
        '|',
        # z vals
        *map(lambda z: fmt.format(z), row)
      ]) for index, row in enumerate(self.Axes['z'].value)
    )
    return f"{x_preceding}{x_axis}\n{x_preceding}{line}\n{zs_with_y}"
    