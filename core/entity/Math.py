from __future__ import annotations
import typing as T
import numpy.typing as npt
# for entities
from .Base import Base, Array, Quantity
# for Math equation parsing
from .. import equation_parser as eq
from ..equation_parser.transformations import (
  FunctionCallTransformer,
  Replacer,
  Evaluator
)
from .Var import Var, BoundVar, FreeVar, LinkedVar, AddressVar
# general stuff
import functools
import numpy as np
import pint

class ConversionFuncType(T.Protocol):
  '''
  Type signature for binary conversion functions, e.g.:
  
  ```
  converter(x: npt.ArrayLike, **kwargs: Dict[str, npt.ArrayLike]) -> Array
  ```

  See [this StackOverflow answer](https://stackoverflow.com/a/64106593) for details on using `typing.Protocol`.
  '''
  def __call__(self, x: npt.ArrayLike, **kwargs: T.Dict[str, npt.ArrayLike]) -> T.Union[Array, Quantity]:
    ...

class Math(Base):
  Vars: T.List[Var] = Base.xpath_synonym('./VAR', many=True)

  LinkedVars: T.List[LinkedVar] = Base.xpath_synonym("./VAR[@type='link']", many=True)

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
    def converter(x: npt.ArrayLike, **kwargs) -> T.Union[Array, Quantity]:
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
      final: T.Union[Array, Quantity] = evaluated.children[0] # type: ignore
      return final
    # set docstring
    signature = f'{first_bound.id}: BoundVar, {kwargs_signature_str}' if free else f'{first_bound.id}: BoundVar'
    # TODO: set ___attributes___
    body = self.attrib['equation']
    #converter.__doc__ = f'converter({signature}) -> np.ndarray: \n  {body}'
    converter.__doc__ = f'{body}'
    return converter
    
  #@functools.cached_property
  @property
  def equation(self) -> eq.SyntaxTree:
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
