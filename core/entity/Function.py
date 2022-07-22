from __future__ import annotations
import typing as t
from .Base import Base, Array, Quantity, ArrayLike, UnitRegistry
import pint
if t.TYPE_CHECKING:
  from . import Axis

from .Parameter import Parameter
import numpy as np
import numpy.typing as npt
from decimal import Decimal, ROUND_HALF_UP

def round_off(number, ndigits=None):
    """
    Always round off. TunerPro indexing always arounds 0.5 => 1
    See https://stackoverflow.com/a/70285861.
    """
    exp = Decimal('1.{}'.format(ndigits * '0')) if ndigits else Decimal('1')
    return type(number)(Decimal(number).quantize(exp, ROUND_HALF_UP))

def increasing(a: npt.ArrayLike) -> np.ma.masked_array:
  '''
  Retain monotonically-increasing subset by masking out values that fall below the max, e.g.
  `[0, 1, 2, 0, -2, 4, 0, -5, 6, 7, 8]` => 
  `[0, 1, 2, -,  -, 4, -,  -, 6, 7, 8]`
  '''
  # https://stackoverflow.com/a/28563925
  high_water = np.maximum.accumulate(a)
  fall_under = high_water - a > 0
  out: np.ma.masked_array = np.ma.masked_array(a, fall_under)
  return out

def gaps(indices: np.ma.masked_array, vals: np.ma.masked_array) -> np.ma.masked_array:
  # [[idx1, val1], [idx2, val2]...]
  idxVal = np.stack(
    (
      round(indices.compressed()),
      vals.compressed()  
    ),
    axis = 1
  )
  # ...indices paired, e.g. [0, 1, 2] -> [0, 1], [1, 2], [2, 3]
  pairs = np.lib.stride_tricks.sliding_window_view(
    np.rot90(idxVal)[1],
    2
  )
  # ...list of idx, val, slice width - greater than one means this is a discontinuity
  boundsAndDiff = np.hstack((pairs, np.diff(pairs)))
  # ...(start, end, diff > 2) means out[start + 1: end] is the non-inclusive empty slice, e.g. [1, 2, 0, -1, 3] 
  gaps = boundsAndDiff[boundsAndDiff[:, 2] > 1]
  return gaps

def monotone_interpolated(values: npt.NDArray, indices: npt.NDArray) -> npt.NDArray:
  '''
  TunerPro uses a unique interpolation strategy when using `Function` as an axis. 
  Fill in the monotone parts using the indices and their matching value, and interpolate the non-monotone parts using the previous value/
  
  v idx     out
  10	0  |   10
  20	1  |   20
  30	2  |   30
  40  3  |   40
  50	0  -    68     np.linspace(60, 70, abs(4.5-0))
  60  0  -    
  70 4.5 |   70
  80  6  |   80
  90  2  -    109.23 np.linspace(100, 110, abs(8 - -5))
  100	-5 -   110
  110 8  |   120
  120 9  |   130
  130 10 |   157.65
  140 -5 -    158.24
  150 -2 -    158.82
         -    159.41
  160 15 |   160
  '''
  # ...segregate increasing subsequences in indices
  monotonic_idx = increasing(indices)
  monotonic_val: np.ma.masked_array = np.ma.masked_array(values, monotonic_idx.mask)
  non_monotonic_idx: np.ma.masked_array = np.ma.masked_array(
    data=indices,
    mask=np.logical_not(monotonic_idx.mask)
  )
  #non_monotonic_val = np.ma.masked_array(
  #  data=values,
  #  mask=non_monotonic_idx.mask
  #)
  #  FILL IN THE BLANKS
  out: Array = Array(np.zeros(values.shape))
  # ...list of idx, val, e.g. [[0, 10], [1, 20]]
  uninterpolated = np.stack(
    (
      round(monotonic_idx.compressed()),
      monotonic_val.compressed()  
    ),
    axis = 1
  )
  # ...indices paired, e.g. [0, 1, 2] -> [0, 1], [1, 2], [2, 3]
  pairs = np.lib.stride_tricks.sliding_window_view(
    np.rot90(uninterpolated)[1],
    2
  )
  # ...list of idx, val, slice width - greater than one means this is a discontinuity
  boundsAndDiff = np.hstack((pairs, np.diff(pairs)))
  # ...(start, end, diff > 2) means out[start + 1: end] is the non-inclusive empty slice, e.g. [1, 2, 0, -1, 3] 
  gaps = boundsAndDiff[boundsAndDiff[:, 2] > 1]
  adjust_start = np.full_like(np.zeros(gaps.shape), [1, 0, 0])
  gaps = gaps + adjust_start
  # fill output with each index's matching value from function
  for index, val in uninterpolated:
    out[int(index)] = val
  # traverse gaps backwards
  #gaps = np.hstack((enumerated, np.flipud(gaps)))
  # for interpolation, fill in empty parts
  clean_indices = round(indices).astype(np.integer)
  for start, end, diff in gaps.astype(np.integer):
    gap = out[start:end]
    rising = np.flatnonzero(values == out[end])[0] - 1, end
    length = abs(
      clean_indices[rising[0] + 1] - clean_indices[rising[0]]
    )
    interpolant = np.linspace(
    # interpolate between end-of-dip value and indexed value
      values[rising[0]], out[rising[1]],
      # length between end of dip coords
      length,
      endpoint = False
    )
    # now take the tail of the full interpoland to fill the gap
    filler = interpolant[-(diff - 1):]
    out[start: end] = filler    
  return out

# TODO: use tunerpro round? 0.5 => 1 always
def round(a: npt.NDArray) -> npt.NDArray:
  return np.around(a, decimals = 0)

class Function(Parameter):
  '''
  XDF Function - an X <-> Y mapping. Very similar to Table, minus a third Z Axis. Apparently common in Ford applications.
  '''
  x: Axis.FunctionAxis = Base.xpath_synonym("./XDFAXIS[@id = 'x']")
  # y index axis is unitless, it's indiices
  y: Axis.FunctionAxis = Base.xpath_synonym("./XDFAXIS[@id = 'y']")

  @property
  def value(self) -> ArrayLike:
    '''
    Column-major list of (x, y) coordinate of function, e.g. [(1, 2), (2, 4)]
    '''
    return np.dstack([self.x.value, self.y.value])

  @property
  def interpolated(self):
    out = monotone_interpolated(self.x.value.magnitude, self.y.value.magnitude)
    return out

__all__ = ['Function']