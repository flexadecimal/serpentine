from abc import abstractmethod, ABC
import typing as t
import lark
import functools
#from .. import GenericTree

# ...because functools.partial object has func as member, need polymorphic
# logic to print 'f(g(h(x)))'
def func_printer(func_like: t.Callable) -> str:
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

# from lark
TreeT = t.TypeVar('TreeT')
ReturnT = t.TypeVar('ReturnT')
class TypeTransformer(lark.Transformer, t.Generic[TreeT, ReturnT]):
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
  def _call_userfunc(self, tree, new_children = None):
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
        wrapper = getattr(func, 'visit_wrapper', None)
        if wrapper is not None:
          return func.visit_wrapper(func, tree.data, children, tree.meta)
        else:
          # original only calls with children, not entirely sure why
          return func([tree.data, children])
      except lark.exceptions.GrammarError as e:
        raise e
      except Exception as e:
        raise lark.exceptions.VisitError(tree.data, tree, e)

  #def transform(self, tree: GenericTree[LeafT, LeafT]) -> ReturnT:
  #  return self._transform_tree(tree)

  @abstractmethod
  def __default__(self, data, children, meta):
    pass

  # this is an ignore because lark Transformers always take Tree as input, not GenericTree
  def transform(self, tree: TreeT) -> ReturnT: # type: ignore
    return self._transform_tree(tree)
