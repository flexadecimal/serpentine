import os
import re
from itertools import (
  groupby
)
import sys
import core.entity.Xdf as xdf

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
        tune = xdf.Xdf.from_path(
          os.path.join(root, xdf_path),
          os.path.join(root, bin_path),
          # ignore invalid
          xdf.MathInterdependence,
          xdf.AxisInterdependence
        )
      except Exception as e:
        raise(e)

      #constants = {c.title: c.value for c in xdf.Constants}
      #tables = {t.title: t.value for t in xdf.Tables}
      functions = {f.title: f for f in tune.Functions}

      for idx, t in enumerate(tune.Tables):
        print(t.title)
        x, y = t.x.value, t.y.value


      zwb = tune.xpath('./XDFCONSTANT[1]')[0]
      ve = tune.xpath('./XDFTABLE[2]')[0]
      #ve_val = ve.value
      # test setters
      zwb.value = 12.24 + 5
      pass
      #ignition_map.value = [2]
