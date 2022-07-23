import typing as t
from .Base import Base, ArrayLike, ReferenceQuantified
from .Math import Math
from .Axis import EmbeddedAxis, QuantifiedEmbeddedAxis
# to avoid circular import
from .Axis import XYAxis
from .Parameter import Parameter, Clamped
import numpy as np
import numpy.typing as npt
import functools
from itertools import (
  chain
)
from .Mask import Mask, MaskedMath
import pint
from pynverse import inversefunc

_math = Math

class GlobalMath(MaskedMath):
  @property
  def mask(self) -> Mask:
    return Mask(np.zeros(self.shape).astype(np.ma.MaskType))

class RowMath(MaskedMath):
  @property
  def row(self):
    return int(self.attrib['row']) - 1

  @property
  def mask(self) -> Mask:
    out = np.zeros(self.shape)
    out[self.row] = np.ones(self.shape[0])
    return Mask(np.logical_not(out))

class ColumnMath(MaskedMath):
  @property
  def column(self):
    return int(self.attrib['col']) - 1

  @property
  def mask(self) -> Mask:
    out = np.zeros(self.shape)
    out[ :, self.column] = np.ones(self.shape[1])
    return Mask(np.logical_not(out))

class CellMath(MaskedMath):
  @property
  def row(self):
    return int(self.attrib['row']) - 1
  
  @property
  def column(self):
    return int(self.attrib['col']) - 1

  @property
  def mask(self) -> Mask:
    out = np.zeros(self.shape)
    out[self.row][self.column] = 1
    return Mask(np.logical_not(out))

class ZAxis(ReferenceQuantified, QuantifiedEmbeddedAxis, Clamped):
  '''
  Special-case axis, generally referred to interchangeably with as a "Table", although the Table really contains the Axes and their related information.
  '''
  Math: t.List[_math] = Base.xpath_synonym('./MATH', many=True) # type: ignore
  global_Math: GlobalMath = Base.xpath_synonym('./MATH[not(@row) and not(@col)]')
  column_Math: t.List[ColumnMath] = Base.xpath_synonym('./MATH[@col and not(@row)]', many=True)
  row_Math: t.List[RowMath] = Base.xpath_synonym('./MATH[@row and not(@col)]', many=True)
  cell_Math: t.List[CellMath] = Base.xpath_synonym('./MATH[@row and @col]', many=True)

  @staticmethod
  def _combine_masks(*masks: Mask, initial: t.Optional[Mask] = None) -> Mask:
    # un-invert combined mask...
    reducer = lambda a, b: np.logical_not(
      # ... after inverting masks so that OR works
      np.ma.mask_or(np.logical_not(a), np.logical_not(b), shrink=False)
    )
    if initial is not None:
      return functools.reduce(reducer, masks, initial) # type: ignore
    else:
      return functools.reduce(reducer, masks) # type: ignore

  def _mask_reduction(
    self,
    accumulator: np.ma.MaskedArray,
    type_math: t.Tuple[t.Type[MaskedMath], MaskedMath],
    group_masks: t.Dict[t.Type[MaskedMath], Mask],
    inverse = False
  ):
    '''
    Used internally in `Table.ZAxis`'s binary conversion, where each `math: MaskedMath` takes a masked view of an original array and converts parts incrementally.
    '''
    type, math = type_math
    # do exclusion of current mask with group masks...
    other_group_masks = {
      klass: mask for klass, mask in group_masks.items()
      if klass is not type
    }
    # construct final mask - CellMath needs no exclusion, its just one cell
    if type is not CellMath:
      # other masks may be empty, in the case of only global equation
      combined_exclusion: npt.NDArray = np.logical_not(
        self._combine_masks(*other_group_masks.values())
      ) if other_group_masks else np.ma.nomask
      # ...combine other groups' exclusion with our own mask
      final_mask = np.ma.mask_or(combined_exclusion, math.mask, shrink=False)
    else:
      final_mask = math.mask
    # ...evaluate
    converter = math.conversion_func if not inverse else math.inverse_conversion_func
    converted = converter(accumulator)
    # converted array may be Quantity or Array, depending on if referenced values had units or not.
    # putmask uses opposite of convention, so True = valid
    # TODO: subclass `pint.Quantity` to provide `np.putmask`?
    to_put = converted
    np.putmask(accumulator, np.logical_not(final_mask), to_put)
    return accumulator

  def table_convert(self, x: npt.NDArray, inverse = False):
    '''
    Equations are replaced by the following in order from lowest to highest priority:
    1. Global table equation
    2. Row equations
    3. Column equations
    4. Cell equations

    TunerPro represents an equation grid in the UI.
    '''
    # see https://github.com/python/mypy/issues/1178 - linter can't discern the explicit length check here. "Table" could be 1D - remember numpy shape convention
    #if len(self.EmbeddedData.shape) == 2:
    #  cols = self.EmbeddedData.shape[1] # type: ignore
    #elif len(self.EmbeddedData.shape) == 1:
    #  cols = 1
    #else:
    #  raise ValueError(f"Incorrect shape {self.EmbeddedData.shape} for Table.ZAxis when constructing equation grid.")

    # TABLE MATH CONVERSION
    # ...in order of lowest to highest precedence
    math_groups: t.Dict[t.Type[MaskedMath], t.List[MaskedMath]] = {
      GlobalMath: [self.global_Math],
      ColumnMath: self.column_Math,
      RowMath: self.row_Math,
      CellMath: self.cell_Math,
    }
    # ...only eval non-empty
    math_groups_nonempty = {
      klass: maths for klass, maths in math_groups.items()
      if maths
    }
    # ...masks must be subtracted - combine masks amongst groups
    combined_masks = {
      klass: self._combine_masks(
        *map(lambda math: math.mask, maths)
      )
      for klass, maths in math_groups_nonempty.items()
      # global math doesn't belong here
      if klass is not GlobalMath
    }
    # ...flatten out into tuple of (Type, MaskedMath instance)
    flattened = (
      ((type, math) for math in maths)
      for type, maths in math_groups_nonempty.items()
    )
    # reduce, providing combined group masks
    out = functools.reduce(
      functools.partial(
        self._mask_reduction,
        group_masks = combined_masks,
        inverse = inverse
      ),
      chain.from_iterable(flattened),
      x
    )
    return out

  def to_embedded(self, x: npt.NDArray) -> ArrayLike:
    copy = x.copy().astype(np.float_)
    out = self.table_convert(copy, inverse=True)
    return out

  def from_embedded(self, x: npt.NDArray) -> ArrayLike:
    copy = x.copy().astype(np.float_)
    out = self.table_convert(copy)
    return out
  

class Table(Parameter):
  '''
  Table, a.k.a array/list of values. Usually this is a 2D table like a fuel or ignition map, or occasionally, a 1D list like an axis, e.g. Major RPM.
  '''
  x: XYAxis = Base.xpath_synonym("./XDFAXIS[@id='x']")
  y: XYAxis = Base.xpath_synonym("./XDFAXIS[@id='y']")
  z: ZAxis = Base.xpath_synonym("./XDFAXIS[@id='z']")

  @property
  def value(self):
    return self.z.value

  @value.setter
  def value(self, value: pint.Quantity):
    self.z.value = value

  def __str__(self):
    sep = ' '
    width = 6
    fmt = f"{{0:>{width}.1f}}"
    x_axis = sep.join(map(
      lambda x: fmt.format(x), self.x.value
    ))
    x_preceding = ' ' * (width + 2 + len(sep))
    line = '-' * len(x_axis) 
    # prepend y value for each z-axis table row
    zs_with_y = '\n'.join(
      sep.join([
        # preceding y val
        fmt.format(self.y.value[index]),
        # divider
       '|',
        # z vals
        *map(lambda z: fmt.format(z), row)
      ]) for index, row in enumerate(self.z.value)
    )
    return f"{x_preceding}{x_axis}\n{x_preceding}{line}\n{zs_with_y}"
    
__all__ = ['Table']