import os
import re
import typing as t
from itertools import (
  groupby
)
import sys
import core.entity.Xdf as xdf

cars_folder = './cars/testing'
car_name_regex = rf"{cars_folder}/(?P<car>[\w+-_]+)"

  # parse car name for dict key
def parse_car_path(car):
  matches = re.search(car_name_regex, car)
  return matches.groups('cars_folder')[0] if matches else None
  
def files_by_type(root, files):
  # split by bin, xdf, adx
  # TODO: actually parse adx
  files_by_type = {ext[1:]: list(files) for ext, files in groupby(files, lambda file: os.path.splitext(file)[1])}
  # TODO: process multiple bins?
  xdf_path = os.path.join(root, files_by_type['xdf'][0])
  bin_path = os.path.join(root, files_by_type['bin'][0])
  # apply xdf parsing to bin file to render scalars and tables
  return xdf_path, bin_path
  
def print_exception(e, folder):
  print(f"""Caught expected `{type(e).__qualname__}` during opening "{folder}".
      
          {e}
      """)

if __name__ == '__main__':
  # car folder name to dict of file handles  
  car_files = {root: files for root, folders, files in os.walk(cars_folder) if parse_car_path(root)}
  # ...to name and full path
  car_to_path = {parse_car_path(root): files_by_type(root, files) for root, files in car_files.items()}

  # EXCEPTION SANITY TESTS
  folder_to_exception = {
    'cyclical-math': xdf.MathInterdependence,
    'cyclical-axes': xdf.AxisInterdependence
  }

  print("CYCLICAL REFERENCES")
  for folder, exception in folder_to_exception.items():
    try:
      xdf_path, bin_path = car_to_path[folder]
      tune = xdf.Xdf.from_path(
        xdf_path,
        bin_path,
        # ignore invalid
        #*exceptions
      )
    except exception as e: # type: ignore
      # we expected these
      print_exception(e, folder)
    except Exception as e:
      raise(e)

  print("BOUNDS CHECKING")
  folder = 'bounds-checking'
  test_xdf, test_bin = car_to_path[folder]
  tune = xdf.Xdf.from_path(
    test_xdf,
    test_bin
  )
  # access tables...
  end = 40
  print('Tables: ')
  for idx, table in enumerate(tune.Tables):
    print(f"  '{table.title[:end]}'...")
    try:
      x = table.x.value,
      y = table.y.value
      z = table.z.value
      pass
    except Exception as e:
      pass
      raise(e)

  # test constant write
  print("\nTEST WRITE BOUNDS")
  zwb = tune.xpath('./XDFCONSTANT[1]')[0]
  try:
    zwb.value = 12.24 + 20
  except xdf.EmbeddedValueError as e:
    print_exception(e, folder)
  try:
    #zwb.value = 12.24 + 20
    ignition_map = tune.Tables[0]
    ignition_map.value += 20
  except xdf.EmbeddedValueError as e:
    print_exception(e, folder)

print("\nTEST FUNCTION INTERPOLATION")
func_test_xdf, func_test_bin = car_to_path['function-parameter']
func_test = xdf.Xdf.from_path(
  func_test_xdf,
  func_test_bin
)
ignition_map = func_test.Tables[0]
function = func_test.Functions[0]
normalized = ignition_map.y.value
# TODO - verify this against printout

print ("\nTEST PATCH PARAMETER")
patch_tune_xdf, patch_tune_bin = car_to_path['patch-parameter']
patch_tune = xdf.Xdf.from_path(
  patch_tune_xdf,
  patch_tune_bin
)
patch = patch_tune.Patches[0]
a = patch.entries[0].patch
pass