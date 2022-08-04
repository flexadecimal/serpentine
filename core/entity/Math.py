from __future__ import annotations
import typing as t
import numpy.typing as npt
# for entities
from .Base import Base, RefersCyclically, CyclicReferenceException, ArrayLike
# for Math equation parsing
from .. import equation_parser as eq
from ..equation_parser.transformations import (
  Replacer,
  Evaluator,
  FunctionCallTransformer
)
from .Var import Var, BoundVar, FreeVar, LinkedVar, AddressVar
# general stuff
import functools
from pynverse import inversefunc
from itertools import chain
from . import Xdf as xdf
import lxml as xml

class MathInterdependence(CyclicReferenceException):
  def __init__(self, xdf: xdf.Xdf, *interdependent_maths: Math):
    self.cycle = interdependent_maths
    # fancy printing
    self.xdf = xdf

  def __str__(self):
    root_tree: xml.ElementTree = self.xdf.getroottree()
    printouts: t.List[str] = []
    for math in self.cycle:
      # var.linked.Math may be a list in case of `Table.ZAxis`, when you have many conversion equation masks
      linked_Maths = set(
        chain.from_iterable(var.linked.Math for var in math.LinkedVars)
      )
      dependent = next(iter(linked_Maths.intersection(self.cycle)))
      dependent_Var = next(filter(
        lambda var: dependent in var.linked.Math, math.LinkedVars
      ))
      # set printout
      printout = "  "
      printout += f"{root_tree.getpath(math.getparent())}: {math.attrib['equation']}"
      printout += f"\n    {dependent_Var.id}: {root_tree.getpath(dependent)}"
      printouts.append(printout)
      seperator = ',\n'
    message = f"""Parameter conversion equations in file `{self.xdf._path}`
    
{seperator.join(printouts)}

are mutually interdependent.
    """
    return message
    #Exception.__init__(self, message)

class Math(RefersCyclically[MathInterdependence, "Math", t.Iterable["Math"]], Base):
  exception = MathInterdependence
  
  @classmethod
  def dependency_graph(cls, xdf) -> t.Mapping[Math, t.Iterable[Math]]:
    has_link: t.Iterable[Math] = xdf.xpath("//MATH[./VAR[@type='link']]")
    # see `Var.LinkedVar`
    #graph = {math:  
    #  list(map(lambda id: self.xpath(f"""
    #    //XDFTABLE[@uniqueid='{id}']/XDFAXIS[@id='z']/MATH | 
    #    //XDFCONSTANT[@uniqueid='{id}']/MATH
    #    """)[0],
    #    math.linked_ids.values()
    #  )) for math in has_link
    #}
    graph = {
      # TODO: flatten math 
      math: list(chain.from_iterable(var.linked.Math for var in math.LinkedVars))
      for math in has_link
    }
    return graph

  Vars: t.List[Var] = Base.xpath_synonym('./VAR', many=True)

  LinkedVars: t.List[LinkedVar] = Base.xpath_synonym("./VAR[@type='link']", many=True)

  # TODO: maybe link should be removed from math?
  DataLink = Base.xpath_synonym('./preceding-sibling::DALINK')

  @property
  def conversion_func(self) -> FunctionCallTransformer.ConversionFunc:
    '''
    Univariate version of `conversion_func` that takes only the binary data as input - internal evaluation order and Vars are used to retreive the arguments.
    '''
    free = list(filter(lambda var: issubclass(type(var), FreeVar), self.Vars))
    kwargs = {var.id: var.value for var in free}
    # save custom docstring
    parameterized = self.conversion_func_parameterized
    curried = functools.partial(parameterized, **kwargs)
    curried.__doc__ = parameterized.__doc__
    return curried # type: ignore

  @property
  def inverse_conversion_func(self) -> FunctionCallTransformer.ConversionFunc:
    '''
    Inverse conversion func, such that inverse(conversion(bin)) = bin.
    This is used to save values to the binary.
    '''
    return inversefunc(self.conversion_func)

  @property
  def conversion_func_parameterized(self) -> FunctionCallTransformer.ConversionFunc:
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
    # now provide namespace so replacement and evaluation can happen later, e.g. 'x*a+b' -> f(x, a=2, b=3)
    kwargs_signature_str = ', '.join(
      f"{var.id}: {var.__class__.__qualname__}" for var in free
    )
    def converter(x: npt.ArrayLike, **kwargs) -> npt.ArrayLike:
      # assert arguments provided by keyword - 
      # TODO: set named args in typed function signature at runtime?
      if not set(var.id for var in free) == set(kwargs.keys()):
        raise ValueError('Invalid variables provided to conversion function.')
      # update namespace with boundvars
      kwargs.update({var.id: x for var in bound})
      # and do full replacement before evaluating
      replaced = Replacer.Replacer(kwargs).transform(self.equation)
      evaluated = Evaluator.Evaluator().transform(replaced)
      # ReturnType<Evaluator.Evaluator()>
      #evaluated: npt.ArrayLike = eq.apply_pipeline(
      #  self.equation,
      #  Replacer.Replacer(kwargs),
      #  Evaluator.Evaluator()
      #)
      return evaluated
    # set docstring
    if bound:
      first_bound, *duplicate_bound = bound
      signature = f'{first_bound.id}: BoundVar, {kwargs_signature_str}' if free else f'{first_bound.id}: BoundVar'
    else:
      signature = f'{kwargs_signature_str}'
    # TODO: set ___attributes___
    body = self.attrib['equation']
    #converter.__doc__ = f'converter({signature}) -> np.ndarray: \n  {body}'
    converter.__doc__ = f'{body}'
    return converter
    
  #@functools.cached_property
  @property
  def equation(self) -> FunctionCallTransformer.FunctionTree:
    equation_str = self.attrib['equation']
    # apply parser and function call transformation in one fell swoop
    equation_ast = FunctionCallTransformer.FunctionCallTransformer(suppress_rounding=True).transform(
      eq.parser(equation_str)
    )
    return equation_ast

  def __repr__(self):
    equation_str = self.attrib['equation']
    #return f"{equation_str}"
    #return f'{self.getroottree().getpath(self)}: {equation_str}'
    return f"<{self.__class__.__name__} eq='{equation_str}'>\n{repr(self.equation)}"
