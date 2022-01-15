import typing as T
from abc import ABC, abstractmethod
from .Base import Base, XmlAbstractBaseMeta, Array, MeasurementMixin, Quantity, ArrayLike
from .EmbeddedData import (
  EmbeddedData, 
  EmbeddedMathMixin, 
)
from .Math import Math
from .Parameter import Parameter
import numpy as np
import numpy.typing as npt
import functools
from itertools import (
  chain
)
import pint

# need this in `Axis` because python thinks we're referring to the property `Axis.Math`
_math = Math

class Axis(Base, EmbeddedMathMixin):
  Labels = Base.xpath_synonym('./LABEL', many=True)
  Math: _math = Base.xpath_synonym('./MATH')
  
  @property
  def units(self):
    '''
    Unit text to display, e.g. "RPM". 
    For display only - data/units are properly typed in `XYAxis`, `ZAxis`.
    '''
    return self.xpath('./units/text()')[0]

  # each axis is a memory-mapped array
  @property
  def value(self) -> ArrayLike:
    out = self.Math.conversion_func(
      self.memory_map.astype(
        np.float64, 
        copy=False
        # use the underlying embedded row/col major ordering, shape, etc.
    ))
    return out

# custom math subclasses for ZAxis with row/col
class Mask(Array[np.ma.MaskType]):
  def __repr__(self):
    # interpret masks as binary for space-saving printing
    return Array.__repr__(self.astype(np.int))

class MaskedMath(Math, ABC, metaclass=XmlAbstractBaseMeta):
  '''
  Specifically for `Table.ZAxis`, `<MATH>` elements with varying attributes must provide a Numpy mask to use in binary conversion.

  See the [Numpy documention on masked arrays](https://numpy.org/doc/stable/reference/maskedarray.html) for more details.

  TunerPro-style table equation matrix has the following `Math` elements in order of lowest to highest precedence. Calculation does not overlap - masks are excluded against others.

  - global table equation has no additional attributes,
  - row `Math` has row attribute,
  - col `Math` has column attirbute,
  - cell `Math` has both row and column.
  '''
  @property
  def shape(self):
    embedded_data: EmbeddedData = self.xpath('./preceding-sibling::EMBEDDEDDATA')[0]
    return embedded_data.shape
  
  @property
  @abstractmethod
  def mask(self) -> Mask:
    '''
    Numpy boolean mask array, following convention of `False` meaning valid data, and `True` meaning invalid data..
    '''
    pass

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

# TODO: X/Y Axes can have stock units and data types, but Z axis does not? weird
class XYAxis(Axis, MeasurementMixin):
  '''
  Table X/Y Axis with Labels from (following TunerPro parlance):
    - "Internal, Pure": binary memory map
    - "External (Manual)": <LABEL> elements
    - "Linked, Normalized": Parameter value, either Constant or Table
    - "Linked, Scale": TODO: figure out
  '''
  @property
  def length(self):
    return int(self.xpath('./indexcount/text()'))

  @property
  def value(self) -> Quantity:
    original = Axis.value.fget(self) # type: ignore
    return pint.Quantity(original, self.unit)

class ZAxis(Axis):
  '''
  Special-case axis, generally referred to interchangeably with as a "Table", although the Table really contains the Axes and their related information.
  '''
  Math: T.List[_math] = Base.xpath_synonym('./MATH', many=True) # type: ignore
  global_Math: GlobalMath = Base.xpath_synonym('./MATH[not(@row) and not(@col)]')
  column_Math: T.List[ColumnMath] = Base.xpath_synonym('./MATH[@col and not(@row)]', many=True)
  row_Math: T.List[RowMath] = Base.xpath_synonym('./MATH[@row and not(@col)]', many=True)
  cell_Math: T.List[CellMath] = Base.xpath_synonym('./MATH[@row and @col]', many=True)

  @staticmethod
  def _combine_masks(*masks: Mask, initial: T.Optional[Mask] = None) -> Mask:
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
    type_math: T.Tuple[T.Type[MaskedMath], MaskedMath],
    group_masks: T.Dict[T.Type[MaskedMath], Mask]
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
      combined_exclusion: npt.ArrayLike = np.logical_not(
        self._combine_masks(*other_group_masks.values())
      ) if other_group_masks else np.ma.nomask
      # ...combine other groups' exclusion with our own mask
      final_mask = np.ma.mask_or(combined_exclusion, math.mask, shrink=False)
    else:
      final_mask = math.mask
    # ...evaluate
    converted = math.conversion_func(accumulator)
    # converted array may be Quantity or Array, depending on if referenced values had units or not.
    # putmask uses opposite of convention, so True = valid
    # TODO: subclass `pint.Quantity` to provide `np.putmask`?
    to_put = converted.magnitude if issubclass(converted.__class__, Quantity) else converted
    np.putmask(accumulator, np.logical_not(final_mask), to_put)
    return accumulator

  @functools.cached_property
  def value(self) -> Array:
    '''
    Equations are replaced by the following in order from lowest to highest priority:
    1. Global table equation
    2. Row equations
    3. Column equations
    4. Cell equations

    TunerPro represents an equation grid in the UI.
    '''
    # see https://github.com/python/mypy/issues/1178 - linter can't discern the explicit length check here. "Table" could be 1D - remember numpy shape convention
    rows = self.EmbeddedData.shape[0]
    if len(self.EmbeddedData.shape) == 2:
      cols = self.EmbeddedData.shape[1] # type: ignore
    elif len(self.EmbeddedData.shape) == 1:
      cols = 1
    else:
      raise ValueError(f"Incorrect shape {self.EmbeddedData.shape} for Table.ZAxis when constructing equation grid.")

    # TABLE MATH CONVERSION
    # ...in order of lowest to highest precedence
    math_groups: T.Dict[T.Type[MaskedMath], T.List[MaskedMath]] = {
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
    combined_masks: T.Dict[T.Type[MaskedMath], npt.NDArray] = {
      klass: self._combine_masks(
        *map(lambda math: math.mask, maths)
      )
      for klass, maths in math_groups_nonempty.items()
      # global math doesn't belong here
      if klass is not GlobalMath
    }
    # ...provide copy for evaluation
    initial = self.memory_map.copy().astype(np.float_)
    # ...flatten out into tuple of (Type, MaskedMath instance)
    flattened = (
      ((type, math) for math in maths)
      for type, maths in math_groups_nonempty.items()
    )
    # reduce, providing combined group masks
    out = functools.reduce(
      functools.partial(
        self._mask_reduction,
        group_masks = combined_masks
      ),
      chain.from_iterable(flattened),
      initial
    )
    return out

class Table(Parameter):
  '''
  Table, a.k.a array/list of values. Usually this is a 2D table like a fuel or ignition map, or occasionally, a 1D list like an axis, e.g. Major RPM.
  '''
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
    