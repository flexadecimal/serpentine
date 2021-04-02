import os
import pdb
import re
from enum import Enum
from itertools import (
  groupby
)

from core import *

cars_folder = './cars'
car_name_regex = rf"{cars_folder}/(?P<car>[\w+-_]+)"

if __name__ == '__main__':
  # parse car name for dict key
  def parse_car_path(car):
    matches = re.search(car_name_regex, car)
    return matches.groups('cars_folder')[0] if matches else None
  # car folder name to dict of file handles  
  car_files = {root: files for root, folders, files in os.walk(cars_folder) if parse_car_path(root)}
  
  for root, files in car_files.items():
    # split by bin, xdf, adx
    # TODO: actually parse adx
    files_by_type = {ext[1:]: list(files) for ext, files in groupby(files, lambda file: os.path.splitext(file)[1])}
    # apply xdf parsing to bin file to render scalars and tables
    for xdf_path, bin_path, adx_path in zip(files_by_type['xdf'], files_by_type['bin'], files_by_type['adx']):
      parser = entity['BinParser'](
        xdf = os.path.join(root, xdf_path),
        adx = os.path.join(root, adx_path),
        bin = os.path.join(root, bin_path)
      )
  