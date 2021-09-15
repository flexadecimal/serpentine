import typing as T
import numpy.typing as npt
# for entities
from .Base import Base, XdfRefMixin, Array
# for Math equation parsing
from .. import equation_parser as eq
from ..equation_parser.transformations import (
  FunctionCallTransformer,
  Replacer,
  Evaluator
)
from lark import UnexpectedInput, Tree
# for Math vars
from .Var import Var, BoundVar, FreeVar, LinkedVar, AddressVar
# general stuff
import functools
import numpy as np
from enum import Flag

# for typing
class ConversionFuncType(T.Protocol):
  '''
  Type signature for binary conversion functions, e.g.:
  
  ```
  converter(x: npt.ArrayLike, **kwargs: Dict[str, npt.ArrayLike]) -> Array
  ```

  See [this StackOverflow answer](https://stackoverflow.com/a/64106593) for details on using `typing.Protocol`.
  '''
  def __call__(self, x: npt.ArrayLike, **kwargs: T.Dict[str, npt.ArrayLike]) -> Array:
    ...

class TypeFlags(Flag):
  '''
  Type flags found in binary conversion - endianness, signed, etc.
  TunerPro uses "LSB first" (big-endian) and "MSB first" (little-endian)
  terminology.
  '''
  SIGNED = 1
  BIG_ENDIAN = 2
  FLOAT = 65536
  COLUMN_MAJOR = 4

class EmbeddedData(Base):
  '''
  Used under Math elements, providing details on parsing internal binary data.
  '''
  @property
  def address(self) -> T.Optional[int]:
    if 'mmedaddress' in self.attrib:
      return int(self.attrib['mmedaddress'], 16)
    else:
      return None
  
  @property
  def length(self) -> int:
    '''
    Length of binary data in bytes.
    '''
    return int(self.attrib['mmedelementsizebits']) // 8

  @property
  def shape(self) -> T.Union[T.Tuple[int], T.Tuple[int, int]]:
    '''
    Shape tuple following Numpy convention - 2D tables like that of `Table.ZAxis` have shape like `(16, 16)` (or occasionally `(16, )` for a 1D table). Constants have shape `(1, )` - a single number that will be broadcoast to an array length 1.
    '''
    if 'mmedrowcount' in self.attrib and 'mmedcolcount' in self.attrib:
      return (int(self.attrib['mmedrowcount']), int(self.attrib['mmedcolcount']))
    elif 'mmedcolcount' in self.attrib:
      return (int(self.attrib['mmedcolcount']), )
    elif 'mmedrowcount' in self.attrib:
      return (int(self.attrib['mmedrowcount']), )
    # this is a Constant
    else:
      return (1, )

  @property
  def type_flags(self) -> TypeFlags:
    if 'mmedtypeflags' in self.attrib:
      return TypeFlags(int(self.attrib['mmedtypeflags'], 16))
    else:
      return TypeFlags(0)
    
  @property
  def data_type(self) -> npt.DTypeLike:
    if TypeFlags.FLOAT in self.type_flags:
      type = 'f'
    elif TypeFlags.SIGNED in self.type_flags:
      type = 'i'
    else:
      type = 'u'
    endianness = '>' if TypeFlags.BIG_ENDIAN in self.type_flags else '<'
    type_str = f'{endianness}{type}{self.length}'
    return np.dtype(type_str)

  # table only
  @property
  def strides(self) -> T.Optional[T.Union[T.Tuple[int], T.Tuple[int, int]]]:
    '''
    Array stride in memory.
    '''
    major = int(self.attrib['mmedmajorstridebits']) // 8
    minor = int(self.attrib['mmedminorstridebits']) // 8
    if len(self.shape) == 2:
      return None if major == 0 and minor == 0 else (major, minor)
    elif len(self.shape) == 1:
      return None if major == 0 else (major, )
    else:
      raise ValueError

class Math(Base):
  Vars: Var = Base.xpath_synonym('./VAR', many=True)

  @property
  def linked_ids(self) -> T.Dict[str, str]:
    linked_vars = self.xpath("./VAR[@type='link']")
    return {link.attrib['id']: link.attrib['linkid'] for link in linked_vars}
  
  # TODO: maybe link should be removed from math?
  DataLink = Base.xpath_synonym('./preceding-sibling::DALINK')

  @property
  def conversion_func(self) -> ConversionFuncType:
    '''
    Univariate version of `conversion_func` that takes only the binary data as input - internal evaluation order and Vars are used to retreive the arguments.
    '''
    free = list(filter(lambda var: issubclass(type(var), FreeVar), self.Vars))
    kwargs = {var.id: var.value for var in free}
    # save custom docstring
    parameterized = self.conversion_func_parameterized
    curried = functools.partial(parameterized, **kwargs)
    curried.__doc__ = parameterized.__doc__
    return curried
    
  @property
  def conversion_func_parameterized(self) -> ConversionFuncType:
    '''
    Binary conversion function with `**kwargs` of declared Linked/Address Vars. Python is nicer with circular references, and TunerPro itself warns of circular references - but to be explicit, evaluation order uses acyclic dependency order to pass Vars as kwargs.
    
    In ADX, this would be serial data - but the signature is still univariate.
    
    TODO: In the future, equation parsing and evaluation may need to be 
    parrallelized (asynchronously/threaded), because it is expensive.
    '''
    # ideally this is length 1, just X - but you *could* specify Y as the same 
    # data, it's nonsense but valid to do - conversion is still univariate...
    bound = list(filter(lambda var: type(var) == BoundVar, self.Vars))
    # free vars are the Linked or Raw Address vars, provided as kwargs
    free = list(filter(lambda var: issubclass(type(var), FreeVar), self.Vars))
    first_bound, *duplicate_bound = bound
    # now provide namespace so replacement and evaluation can happen later, e.g. 'x*a+b' -> f(x, a=2, b=3)
    kwargs_signature_str = ', '.join(
      f"{var.id}: {var.__class__.__qualname__}" for var in free
    )
    def converter(x: npt.ArrayLike, **kwargs) -> Array:
      # assert arguments provided by keyword - 
      # TODO: set named args in typed function signature at runtime?
      if not set(var.id for var in free) == set(kwargs.keys()):
        raise ValueError('Invalid variables provided to conversion function.')
      # update namespace with boundvars
      kwargs.update({var.id: x for var in bound})
      a = 2
      # and do full replacement before evaluating
      evaluated = eq.apply_pipeline(
        self.equation,
        Replacer.Replacer(kwargs),
        Evaluator.Evaluator()
      )
      # implicit `statement` root in tree, take eval'd child
      return evaluated.children[0]
    # set docstring
    signature = f'{first_bound.id}: BoundVar, {kwargs_signature_str}' if free else f'{first_bound.id}: BoundVar'
    body = self.attrib['equation']
    #converter.__doc__ = f'converter({signature}) -> np.ndarray: \n  {body}'
    converter.__doc__ = f'{body}'
    return converter
    
  #@functools.cached_property
  @property
  def equation(self) -> Tree:
    equation_str = self.attrib['equation']
    # apply parser and function call transformation in one fell swoop
    equation_ast = eq.apply_pipeline(
      eq.parser(equation_str),
      FunctionCallTransformer.FunctionCallTransformer()
    )
    return equation_ast

    
  def __repr__(self):
    equation_str = self.attrib['equation']
    #return f"{equation_str}"
    return f'{self.getroottree().getpath(self)}: {equation_str}'
    #return f"<{self.__class__.__name__} eq='{equation_str}'>\n{eq.ast_print(self.equation)}"

class EmbeddedMathMixin(XdfRefMixin):
  '''
  Mixin for objects exposing a value using both `<MATH>` and `<EMBEDDEDDATA>`.
  `Constant` and `Table.Axis` do this. `Table` has a value itself, but its value is constructed from "real" `EmbeddedMathMixin` memory maps.
  '''
  EmbeddedData: EmbeddedData = Base.xpath_synonym('./EMBEDDEDDATA')

  @functools.cached_property
  def memory_map(self) -> Array:
    embedded_data = self.EmbeddedData
    map: npt.NDArray = np.memmap(
      self._xdf._binfile,
      shape = embedded_data.shape,
      # see TunerPro docs - base offset not applied here
      offset = embedded_data.address,
      dtype = embedded_data.data_type,
      # 'C' for C-style row-major, 'F' for Fortran-style col major 
      order = 'F' if TypeFlags.COLUMN_MAJOR in embedded_data.type_flags else 'C',
    )
    # set strides, if they exist - default XML stride of (0,0) is invalid
    if embedded_data.strides:
      map.strides = embedded_data.strides
    return Array(map)