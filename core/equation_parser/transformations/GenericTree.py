import typing as t
import lark
from .TypeVisitors import TypeTransformer, func_printer

class Printer(TypeTransformer[t.Any, lark.Tree[str]]):
  '''
  This transformation is used in printing ASTs internally by converting values of other types to their string representations.
  '''  
  # TODO - fix v_args not working here
  #@v_args(inline=True)
  def function(self, args):
    func: t.Callable = args[0]
    func_args: t.List[t.Any]= args[1]
    return lark.Tree(f"<function '{func_printer(func)}'>", func_args)
  
  def __default__(self, data, children, meta):
    return lark.Tree(str(data), children, meta)

Parent = t.TypeVar('Parent')
Leaf = t.TypeVar('Leaf')
Branch = t.Union[Leaf, lark.Tree[Leaf]]
class GenericTree(lark.Tree[Leaf], t.Generic[Parent, Leaf]):  
  # we are overriding type for our typechecking, but this is functionally same as Lark tree,
  # just a hack to have differently typed data AND children
  data: Parent # type: ignore
  
  def __init__(self, data: Parent, children, meta = None) -> None:
    self.data = data
    self.children = children
    self._meta = meta

  @classmethod
  def from_tree(cls, Tree: lark.Tree):
    out = cls.__new__(cls)
    return out

  def __repr__(self):
    return ast_print(self)

def ast_print(tree: GenericTree) -> str:
  printer = Printer(visit_tokens = True)
  stringified = printer.transform(tree)
  return stringified.pretty()