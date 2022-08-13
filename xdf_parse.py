import os
from pathlib import Path
import re
import typing as t
import itertools as it
import core.entity.Xdf as xdf
import numpy as np

class TuneFolder(t.NamedTuple):
  xdfs: t.List[Path]
  bins: t.List[Path]

cars_folder = './cars/testing'
car_name_regex = rf"{cars_folder}/(?P<car>[\w+-_]+)"

# TODO: parse export files into Xdfs to check for equality

# parse car name for dict key
def parse_car_path(car):
  matches = re.search(car_name_regex, car)
  return matches.groups('cars_folder')[0] if matches else None
  
def files_by_type(root, files) -> TuneFolder:
  # split by bin, xdf, adx
  # TODO: actually parse adx
  # input to groupby needs to be sorted. see https://stackoverflow.com/a/50198641
  key = lambda file_ext_tup: file_ext_tup[1]
  file_ext_tup = sorted(map(lambda f: os.path.splitext(f), files), key=key)
  grouped_by_extension = it.groupby(file_ext_tup, key)
  #grouped_by_extension = [(f, list(e)) for f, e in grouped_by_extension]
  files_by_type = {ext[1:]: list(it.starmap(lambda f, e: f"{f}{e}", tups)) for ext, tups in grouped_by_extension}
  xdf_paths = list(map(
    lambda f: Path(os.path.join(root, f)),
    files_by_type['xdf']
  ))
  bin_paths = list(map(
    lambda f: Path(os.path.join(root, f)),
    files_by_type['bin']
  ))
  # apply xdf parsing to bin file to render scalars and tables
  return TuneFolder(
    xdfs = xdf_paths,
    bins = bin_paths
  )
  
def print_exception(e, folder):
  print(f"""Caught expected `{type(e).__qualname__}` during opening "{folder}".
{e}
""")

def test_flag(folder: TuneFolder):
  print("\nTEST FLAG PARAMETER")
  flag_xdf, flag_bin = folder.xdfs[0], folder.bins[0]
  flag_tune = xdf.Xdf.from_path(
    flag_xdf,
    flag_bin
  )
  flag = flag_tune.Flags[0]
  print(flag.value)
  # set flag value
  flag.value = not flag.value
  print(flag.value)

def test_patch(folder: TuneFolder):
  print("\nTEST PATCH PARAMETER")
  xdf_by_name = {path.stem: path for path in folder.xdfs}
  bin_by_name = {path.stem: path for path in folder.bins}
  no_basedata_xdf, edited_bin = xdf_by_name['no_basedata'], bin_by_name['edited']
  original_xdf, original_bin = xdf_by_name['rev5b'], bin_by_name['original']
  original = xdf.Xdf.from_path(
    original_xdf,
    original_bin
  )
  cant_unpatch = xdf.Xdf.from_path(
    no_basedata_xdf,
    edited_bin
  )
  reversible_patch = original.Patches[0]
  unreversible_patch = cant_unpatch.Patches[0]
  # test functionality...
  # ...this should work
  # TODO: before and after
  reversible_patch.apply_all()
  reversible_patch.remove_all()
  # ...this should break
  unreversible_patch.apply_all()
  try:
    unreversible_patch.remove_all()
  except xdf.UnpatchableError as e:
    print_exception(e, "patch-parameter")

def test_function(folder: TuneFolder):
  print("\nTEST FUNCTION INTERPOLATION")
  func_test_xdf, func_test_bin = folder.xdfs[0], folder.bins[0]
  func_test = xdf.Xdf.from_path(
    func_test_xdf,
    func_test_bin
  )
  ignition_map = func_test.Tables[0]
  function = func_test.Functions[0]
  normalized = ignition_map.y.value
  # TODO - verify this against printout

def test_write_bounds(folder: TuneFolder):
  print("\nTEST WRITE BOUNDS")
  test_xdf, test_bin = folder.xdfs[0], folder.bins[0]
  tune = xdf.Xdf.from_path(
    test_xdf,
    test_bin
  )
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

def test_list_values(folder: TuneFolder):
  test_xdf, test_bin = folder.xdfs[0], folder.bins[0]
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

def test_cyclicality():
  # EXCEPTION SANITY TESTS
  folder_to_exception = {
    'cyclical-math': xdf.MathInterdependence,
    'cyclical-axes': xdf.AxisInterdependence
  }

  print("CYCLICAL REFERENCES")
  for folder, exception in folder_to_exception.items():
    try:
      xdf_path, bin_path = car_to_path[folder].xdfs[0], car_to_path[folder].bins[0]
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

def test_equation_parser(folder: TuneFolder):
  test_xdf, test_bin = folder.xdfs[0], folder.bins[0]
  tune = xdf.Xdf.from_path(
    test_xdf,
    test_bin
  )
  #ignition_map = tune.Tables[0]
 #val = ignition_map.value
  #ve = tune.Tables[1]
  #ve_x = ve.x.value
  #ve_y = ve.y.value
  #ve_z = ve.z.value
  tlw = tune.Tables[2]
  tlw_y = tlw.y.value
  pass


if __name__ == '__main__':
  # car folder name to dict of file handles  
  car_files = {root: files for root, folders, files in os.walk(cars_folder) if parse_car_path(root)}
  # ...to name and full path
  car_to_path = {parse_car_path(root): files_by_type(root, files) for root, files in car_files.items()}

  #test_cyclicality()
  #test_list_values(car_to_path['bounds-checking'])
  #test_write_bounds(car_to_path['bounds-checking'])
  #test_function(car_to_path['function-parameter'])
  #test_patch(car_to_path['patch-parameter'])
  #test_flag(car_to_path['flag-parameter'])
  test_equation_parser(car_to_path['equation-parser'])
  pass