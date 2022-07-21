import typing as T
from lark import (
  Tree
)
from lark.visitors import (
  Transformer, Interpreter, Discard
)
from lark.exceptions import (
  VisitError, GrammarError
)
import functools

# ...because functools.partial object has func as member, need polymorphic
# logic to print 'f(g(h(x)))'
def func_printer(func_like: T.Callable) -> str:
  if type(func_like) == functools.partial:
    return func_like.func.__name__
  else:
    return func_like.__name__

def type_disambiguator(data) -> str:
    '''
    Rather than using type(data).__name__ directly, this function dispatches the type name. This allows for numpy ufuncs and python functions to be referred to via `function` rather than seperately as `ufunc`, `function`.
    '''
    if callable(data):
      return 'function'
    else:
      return type(data).__name__  

class TypeTransformer(Transformer):
  '''
  Custom subclass of Lark's Transformer that allows for traversal of typed data.
  In this application, we render a function call tree from the Lark AST, e.g.
  
  ```
  x+30+SIN(x)
  statement
    <function sum>
      x
      30
      <function sin>
        x
  ```
  Classic Lark Transformer uses string value, so it would attempt to look up via getattr,
  where TypeTransformer will use the type of the data element.
  '''
  # see https://github.com/lark-parser/lark/blob/master/lark/visitors.py
  def _call_userfunc(self, tree: Tree, new_children = None):
    children = new_children if new_children is not None else tree.children
    try:
      func = getattr(
        self,
        type_disambiguator(tree.data),
      )
    except AttributeError:
      return self.__default__(tree.data, children, tree.meta) # type: ignore
    else:
      try:
        wrapper: T.Optional[T.Callable] = getattr(func, 'visit_wrapper', None)
        if wrapper is not None:
          return func.visit_wrapper(func, tree.data, children, tree.meta)
        else:
          # original only calls with children, not entirely sure why
          return func([tree.data, children])
      except GrammarError as e:
        raise e
      except Exception as e:
        raise VisitError(tree.data, tree, e)

  #def _call_userfunc_token(self, token):
  #  pass

class TypeInterpreter(Interpreter):
  '''
  Type-dispatch Visitor. See ``TypeTransformer``.
  '''
  def visit(self, tree):
    try:
      func: T.Callable = getattr(self, type_disambiguator(tree.data))
    except AttributeError:
      return self.__default__(tree)
    else:
      try:
        wrapper = getattr(func, 'visit_wrapper', None)
        if wrapper is not None:
          return func.visit_wrapper(func, tree.data, tree.children, tree.meta)
        else:
          return func(tree)
      except GrammarError as e:
        raise e
      except Exception as e:
        raise VisitError(tree.data, tree, e)

    #def _call_userfunc_token(self, token):
    #  pass