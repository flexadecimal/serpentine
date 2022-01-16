import typing as t
from enum import Enum
from .Base import Base, XdfRefMixin

class Category(Base):
  name = Base.xpath_synonym('./@name')

  @property
  def index(self) -> int:
    return int(self.xpath('./@index'))

class Categorized(Base, XdfRefMixin):
  '''
  Exposes XML `<CATEGORYMEM>` reference to Xdf header's `<CATEGORY>`s
  as an opaque list of Enum tokens.
  '''
  # TODO: T.List[CategoryEnum]?
  @property
  def categories(self) -> t.List[Category]:
    refs = self.xpath('./CATEGORYMEM')
    return list(map(
      lambda el: self._xdf.Categories[int(el.attrib['category']) - 1],
      refs
    ))