import os
import re
from enum import Enum
from itertools import (
  groupby
)
import sys
from core.entity.Math import Math
from core.entity.Xdf import Xdf, MathInterdependence

import pdb

cars_folder = './cars/testing'
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
      print(f"Opening '{os.path.join(root, xdf_path)}'...")
      try:
        xdf = Xdf.from_path(
          os.path.join(root, xdf_path),
          os.path.join(root, bin_path)
        )
      except MathInterdependence:
        print(f"Xdf '{xdf_path}' is invalid.")

      constants = {c.title: c.value for c in xdf.Constants}
      tables = {t.title: t.value for t in xdf.Tables}

      ignition_map = xdf.xpath('./XDFTABLE[1]')[0]
      #val = ignition_map.value
      major_rpm = xdf.xpath('./XDFTABLE[5]')[0]
      #val = major_rpm.Axes['x'].value
      zwb = xdf.xpath('./XDFCONSTANT[1]')[0].value
      x_axis = ignition_map.Axes['x'].value
      y_axis = ignition_map.Axes['y'].value
      pass
