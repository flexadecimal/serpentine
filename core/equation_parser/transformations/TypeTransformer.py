from lark import (
  Tree
)
from lark.visitors import (
  Transformer, Discard
)
from lark.exceptions import (
  VisitError, GrammarError
)

class TypeTransformer(Transformer):
  '''
  Custom subclass of Lark's Transformer that allows for traversal of typed data.
  In this application, we render a function call tree from the Lark AST, e.g.
  
  x+30+SIN(x)
  statement
    <function sum>
      x
      30
      <function sin>
        x
  
  Classic Lark Visitor uses string value, so it would attempt to look up via getattr,
  where TypeVisitor will use the type of the data element.
  '''
  @staticmethod
  def type_disambiguator(data):
    '''
    Rather than using type(data).__name__ directly, this function dispatches the type name. This allows for numpy ufuncs and python functions to be referred to via `function` rather than seperately as `ufunc`, `function`.
    '''
    if callable(data):
      return 'function'
    else:
      return type(data).__name__
  
  # see https://github.com/lark-parser/lark/blob/master/lark/visitors.py
  def _call_userfunc(self, tree, new_children = None):
    children = new_children if new_children is not None else tree.children
    try:
      func = getattr(
        self,
        self.type_disambiguator(tree.data),
      )
    except AttributeError:
      return self.__default__(tree.data, children, tree.meta)
    else:
      try:
        wrapper = getattr(func, 'visit_wrapper', None)
        if wrapper is not None:
          return func.visit_wrapper(func, tree.data, children, tree.meta)
        else:
          # original only calls with children, not entirely sure why
          return func([tree.data, children])
      except (GrammarError, Discard):
        raise
      except Exception as e:
        raise VisitError(tree.data, tree, e)
