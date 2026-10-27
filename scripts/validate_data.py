#!/usr/bin/env python3
"""Validate repository JSON data without external dependencies."""

from __future__ import annotations

import json
import os
from pathlib import Path
import stat
from typing import Any


DATA_PATHS = (
  Path("package.json"),
  Path("src/provinces.json"),
  Path("src/districts.json"),
  Path("src/subdistricts.json"),
  Path("src/geography.json"),
  Path("src/multi-postal-codes.json"),
)
MAX_JSON_BYTES = 16 * 1024 * 1024

RECORD_SCHEMAS = {
  "src/provinces.json": {
    "id": int,
    "provinceCode": int,
    "provinceNameEn": str,
    "provinceNameTh": str,
  },
  "src/districts.json": {
    "id": int,
    "provinceCode": int,
    "districtCode": int,
    "districtNameEn": str,
    "districtNameTh": str,
    "postalCode": int,
  },
  "src/subdistricts.json": {
    "id": int,
    "provinceCode": int,
    "districtCode": int,
    "subdistrictCode": int,
    "subdistrictNameEn": str,
    "subdistrictNameTh": str,
    "postalCode": int,
    "postalCodes": list,
  },
  "src/geography.json": {
    "id": int,
    "provinceCode": int,
    "provinceNameEn": str,
    "provinceNameTh": str,
    "districtCode": int,
    "districtNameEn": str,
    "districtNameTh": str,
    "subdistrictCode": int,
    "subdistrictNameEn": str,
    "subdistrictNameTh": str,
    "postalCode": int,
    "postalCodes": list,
  },
}

UNIQUE_FIELDS = {
  "src/provinces.json": ("id", "provinceCode"),
  "src/districts.json": ("id", "districtCode"),
  "src/subdistricts.json": ("id", "subdistrictCode"),
  "src/geography.json": ("id", "subdistrictCode"),
}

IDENTIFIER_FIELDS = ("subdistrictCode", "districtCode", "provinceCode", "id")
CODE_WIDTHS = {
  "provinceCode": (10, 99, "two"),
  "districtCode": (1000, 9999, "four"),
  "subdistrictCode": (100000, 999999, "six"),
}


def validate_code_width(label: str, field: str, value: int, errors: list[str]) -> None:
  minimum, maximum, width = CODE_WIDTHS[field]
  if not minimum <= value <= maximum:
    errors.append(f"{label}: field '{field}' must be a {width}-digit integer")


class DuplicateJsonKeyError(ValueError):
  def __init__(self, key: str) -> None:
    self.key = key


class InvalidJsonConstantError(ValueError):
  def __init__(self, constant: str) -> None:
    self.constant = constant


class SymbolicLinkJsonFileError(OSError):
  pass


class NonRegularJsonFileError(OSError):
  pass


class OversizedJsonFileError(OSError):
  pass


def reject_nonfinite_json_constant(constant: str) -> None:
  raise InvalidJsonConstantError(constant)


def reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
  result: dict[str, Any] = {}
  for key, value in pairs:
    if key in result:
      raise DuplicateJsonKeyError(key)
    result[key] = value
  return result


def reject_symbolic_link(mode: int) -> None:
  if stat.S_ISLNK(mode):
    raise SymbolicLinkJsonFileError


def open_directory(path: Path) -> int:
  descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
  if not stat.S_ISDIR(os.fstat(descriptor).st_mode):
    os.close(descriptor)
    raise NonRegularJsonFileError
  return descriptor


def open_parent_directory(root: Path, relative_path: Path) -> int:
  descriptor = open_directory(root)
  try:
    for part in relative_path.parts[:-1]:
      mode = os.stat(part, dir_fd=descriptor, follow_symlinks=False).st_mode
      reject_symbolic_link(mode)
      if not stat.S_ISDIR(mode):
        raise NonRegularJsonFileError
      next_descriptor = os.open(
        part,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
        dir_fd=descriptor,
      )
      if not stat.S_ISDIR(os.fstat(next_descriptor).st_mode):
        os.close(next_descriptor)
        raise NonRegularJsonFileError
      os.close(descriptor)
      descriptor = next_descriptor
  except BaseException:
    os.close(descriptor)
    raise
  return descriptor


def read_json_file(root: Path, relative_path: Path) -> str:
  directory_descriptor = open_parent_directory(root, relative_path)
  try:
    filename = relative_path.name
    mode = os.stat(filename, dir_fd=directory_descriptor, follow_symlinks=False).st_mode
    reject_symbolic_link(mode)
    if not stat.S_ISREG(mode):
      raise NonRegularJsonFileError
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    with os.fdopen(os.open(filename, flags, dir_fd=directory_descriptor), "rb") as file:
      if not stat.S_ISREG(os.fstat(file.fileno()).st_mode):
        raise NonRegularJsonFileError
      contents = file.read(MAX_JSON_BYTES + 1)
  finally:
    os.close(directory_descriptor)
  if len(contents) > MAX_JSON_BYTES:
    raise OversizedJsonFileError
  return contents.decode("utf-8")


def discover_src_json_paths(root: Path, errors: list[str]) -> list[Path]:
  root_descriptor = open_directory(root)
  try:
    src_mode = os.stat("src", dir_fd=root_descriptor, follow_symlinks=False).st_mode
    reject_symbolic_link(src_mode)
    if not stat.S_ISDIR(src_mode):
      raise NonRegularJsonFileError
    src_descriptor = os.open(
      "src", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root_descriptor
    )
  except SymbolicLinkJsonFileError:
    errors.append("src: symbolic links are not allowed")
    return []
  except NonRegularJsonFileError:
    errors.append("src: must be a directory")
    return []
  finally:
    os.close(root_descriptor)

  paths: list[Path] = []

  def visit(directory_descriptor: int, relative_directory: Path) -> None:
    try:
      for name in os.listdir(directory_descriptor):
        relative_path = relative_directory / name
        mode = os.stat(name, dir_fd=directory_descriptor, follow_symlinks=False).st_mode
        if stat.S_ISLNK(mode):
          if name.endswith(".json"):
            paths.append(relative_path)
          else:
            errors.append(f"{relative_path}: symbolic links are not allowed")
          continue
        if name.endswith(".json"):
          paths.append(relative_path)
          continue
        if stat.S_ISDIR(mode):
          nested_descriptor = os.open(
            name,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
            dir_fd=directory_descriptor,
          )
          if not stat.S_ISDIR(os.fstat(nested_descriptor).st_mode):
            os.close(nested_descriptor)
            errors.append(f"{relative_path}: must be a directory")
          else:
            visit(nested_descriptor, relative_path)

    finally:
      os.close(directory_descriptor)

  visit(src_descriptor, Path("src"))
  return paths


def validate_unique_fields(
  relative_path: str, records: object, fields: tuple[str, ...], errors: list[str]
) -> None:
  if not isinstance(records, list):
    return
  for field in fields:
    seen: dict[object, int] = {}
    for index, record in enumerate(records):
      if not isinstance(record, dict) or field not in record:
        continue
      value = record[field]
      try:
        hash(value)
      except TypeError:
        continue
      if value in seen:
        errors.append(
          f"{relative_path}: duplicate {field} {value!r} at records {seen[value]} and {index}"
        )
      else:
        seen[value] = index


def index_by(records: object, field: str) -> dict[object, dict[str, Any]]:
  if not isinstance(records, list):
    return {}
  index: dict[object, dict[str, Any]] = {}
  for record in records:
    if not isinstance(record, dict) or field not in record:
      continue
    try:
      index[record[field]] = record
    except TypeError:
      continue
  return index


def validate_postal_codes(
  relative_path: str, index: int, record: dict[str, Any], errors: list[str]
) -> None:
  label = record_label(Path(relative_path), index, record)
  postal_codes = record.get("postalCodes")
  if not isinstance(postal_codes, list):
    return
  if not postal_codes:
    errors.append(f"{label}: postalCodes must be a non-empty list")
    return
  if not isinstance(postal_codes[0], dict) or postal_codes[0].get("isPrimary") is not True:
    errors.append(f"{label}: postalCodes[0] must be primary")
  primary_entries: list[dict[str, Any]] = []
  seen_codes: set[int] = set()
  for postal_index, postal_entry in enumerate(postal_codes):
    entry_label = f"{label}: postalCodes[{postal_index}]"
    if not isinstance(postal_entry, dict):
      errors.append(f"{entry_label} must be an object")
      continue
    postal_code = postal_entry.get("postalCode")
    if type(postal_code) is not int:
      errors.append(f"{entry_label}.postalCode must be a five-digit integer")
    else:
      if postal_code in seen_codes:
        errors.append(f"{label}: duplicate postal code {postal_code}")
      else:
        seen_codes.add(postal_code)
      if not 10000 <= postal_code <= 99999:
        errors.append(f"{entry_label}.postalCode must be a five-digit integer")
    if type(postal_entry.get("isPrimary")) is not bool:
      errors.append(f"{entry_label}.isPrimary must be a boolean")
    elif postal_entry["isPrimary"]:
      primary_entries.append(postal_entry)
    for field in ("detailTh", "detailEn"):
      value = postal_entry.get(field)
      if not isinstance(value, str) or not value.strip():
        errors.append(f"{entry_label}.{field} must be a non-empty string")
  if len(primary_entries) != 1:
    errors.append(f"{label}: postalCodes must have exactly one primary entry")
  elif primary_entries[0].get("postalCode") != record.get("postalCode"):
    errors.append(
      f"{label}: primary postal code {primary_entries[0].get('postalCode')!r} "
      f"does not match postalCode {record.get('postalCode')!r}"
    )


def validate_multi_postal(datasets: dict[str, Any], errors: list[str]) -> None:
  relative_path = "src/multi-postal-codes.json"
  data = datasets.get(relative_path)
  if not isinstance(data, dict):
    errors.append(f"{relative_path}: expected object")
    return
  source = data.get("source")
  if not isinstance(source, dict):
    errors.append(f"{relative_path}: source must be an object")
  else:
    for field in ("document", "title", "note", "generatedAt"):
      value = source.get(field)
      if not isinstance(value, str) or not value.strip():
        errors.append(f"{relative_path}: source.{field} must be a non-empty string")
  count = data.get("count")
  entries = data.get("subdistricts")
  if type(count) is not int:
    errors.append(f"{relative_path}: count must be an integer")
  if not isinstance(entries, list):
    errors.append(f"{relative_path}: subdistricts must be a list")
    return
  if type(count) is int and count != len(entries):
    errors.append(f"{relative_path}: count {count} does not match subdistricts length {len(entries)}")
  subdistricts = index_by(datasets.get("src/subdistricts.json"), "subdistrictCode")
  geography = index_by(datasets.get("src/geography.json"), "subdistrictCode")
  expected_codes = {
    code
    for code, record in subdistricts.items()
    if isinstance(record.get("postalCodes"), list) and len(record["postalCodes"]) > 1
  }
  observed_codes: set[object] = set()
  seen_codes: dict[object, int] = {}
  for index, entry in enumerate(entries):
    if not isinstance(entry, dict):
      errors.append(f"{relative_path}[{index}]: expected object")
      continue
    label = record_label(Path(relative_path), index, entry)
    required_types = {
      "provinceCode": int,
      "provinceNameTh": str,
      "districtCode": int,
      "districtNameTh": str,
      "subdistrictCode": int,
      "subdistrictNameTh": str,
      "postalCode": int,
      "postalCodes": list,
      "sourceLines": list,
    }
    for field, expected_type in required_types.items():
      value = entry.get(field)
      if type(value) is not expected_type:
        expected_name = "integer" if expected_type is int else expected_type.__name__
        errors.append(f"{label}: field '{field}' must be a {expected_name}")
      elif expected_type is str and isinstance(value, str) and not value.strip():
        errors.append(f"{label}: field '{field}' must be a non-empty string")
      elif field in CODE_WIDTHS and type(value) is int:
        validate_code_width(label, field, value, errors)
    validate_postal_codes(relative_path, index, entry, errors)
    source_lines = entry.get("sourceLines")
    if isinstance(source_lines, list) and not source_lines:
      errors.append(f"{label}: sourceLines must be a non-empty list")
    elif isinstance(source_lines, list):
      for line_index, line in enumerate(source_lines):
        if not isinstance(line, str) or not line.strip():
          errors.append(f"{label}: sourceLines[{line_index}] must be a non-empty string")
    code = entry.get("subdistrictCode")
    if type(code) is not int:
      continue
    if code in seen_codes:
      errors.append(
        f"{relative_path}: duplicate subdistrictCode {code!r} "
        f"at entries {seen_codes[code]} and {index}"
      )
    else:
      seen_codes[code] = index
    observed_codes.add(code)
    subdistrict = subdistricts.get(code)
    if subdistrict is None:
      errors.append(f"{label}: unknown subdistrictCode {code!r}")
      continue
    for field in ("provinceCode", "districtCode", "subdistrictNameTh", "postalCode", "postalCodes"):
      if entry.get(field) != subdistrict.get(field):
        errors.append(f"{label}: {field} does not match src/subdistricts.json")
    geography_record = geography.get(code)
    if geography_record is not None:
      for field in ("provinceNameTh", "districtNameTh"):
        if entry.get(field) != geography_record.get(field):
          errors.append(f"{label}: {field} does not match src/geography.json")
  if observed_codes != expected_codes:
    missing = sorted(expected_codes - observed_codes, key=repr)
    unexpected = sorted(observed_codes - expected_codes, key=repr)
    errors.append(
      f"{relative_path}: subdistrictCode set does not match multi-postal source "
      f"(missing={missing}, unexpected={unexpected})"
    )


def indexed_record(index: dict[object, dict[str, Any]], key: object) -> dict[str, Any] | None:
  try:
    return index.get(key)
  except TypeError:
    return None


def validate_geography_subdistrict_keys(datasets: dict[str, Any], errors: list[str]) -> None:
  subdistricts = datasets.get("src/subdistricts.json")
  geography = datasets.get("src/geography.json")
  if not isinstance(subdistricts, list) or not isinstance(geography, list):
    return
  expected_codes = {
    record["subdistrictCode"]
    for record in subdistricts
    if isinstance(record, dict) and type(record.get("subdistrictCode")) is int
  }
  observed_codes = {
    record["subdistrictCode"]
    for record in geography
    if isinstance(record, dict) and type(record.get("subdistrictCode")) is int
  }
  missing = sorted(expected_codes - observed_codes, key=repr)
  unexpected = sorted(observed_codes - expected_codes, key=repr)
  if missing or unexpected:
    errors.append(
      "src/geography.json: subdistrictCode set does not match "
      f"src/subdistricts.json (missing={missing}, unexpected={unexpected})"
    )


def validate_foreign_keys(datasets: dict[str, Any], errors: list[str]) -> None:
  provinces = index_by(datasets.get("src/provinces.json"), "provinceCode")
  districts = index_by(datasets.get("src/districts.json"), "districtCode")
  subdistricts = index_by(datasets.get("src/subdistricts.json"), "subdistrictCode")
  for relative_path in ("src/districts.json", "src/subdistricts.json", "src/geography.json"):
    records = datasets.get(relative_path)
    if not isinstance(records, list):
      continue
    for index, record in enumerate(records):
      if not isinstance(record, dict):
        continue
      label = record_label(Path(relative_path), index, record)
      province_code = record.get("provinceCode")
      if indexed_record(provinces, province_code) is None:
        errors.append(f"{label}: unknown provinceCode {province_code!r}")
      if relative_path != "src/districts.json":
        district_code = record.get("districtCode")
        district = indexed_record(districts, district_code)
        if district is None:
          errors.append(f"{label}: unknown districtCode {district_code!r}")
        elif relative_path == "src/subdistricts.json" and record.get("provinceCode") != district.get("provinceCode"):
          errors.append(
            f"{label}: provinceCode {record.get('provinceCode')!r} does not match "
            f"src/districts.json (districtCode={district_code!r})"
          )
  geography = datasets.get("src/geography.json")
  if not isinstance(geography, list):
    return
  sources = (
    ("provinceCode", provinces, "src/provinces.json", ("provinceNameEn", "provinceNameTh")),
    ("districtCode", districts, "src/districts.json", ("provinceCode", "districtNameEn", "districtNameTh")),
    (
      "subdistrictCode",
      subdistricts,
      "src/subdistricts.json",
      ("id", "provinceCode", "districtCode", "subdistrictNameEn", "subdistrictNameTh", "postalCode", "postalCodes"),
    ),
  )
  for index, record in enumerate(geography):
    if not isinstance(record, dict):
      continue
    label = record_label(Path("src/geography.json"), index, record)
    for key_field, source_records, source_path, fields in sources:
      source_record = indexed_record(source_records, record.get(key_field))
      if source_record is None:
        continue
      for field in fields:
        if record.get(field) != source_record.get(field):
          errors.append(
            f"{label}: field '{field}' does not match {source_path} "
            f"({key_field}={record.get(key_field)!r})"
          )


def record_label(relative_path: Path, index: int, record: object) -> str:
  identifier = "unknown"
  if isinstance(record, dict):
    for field in IDENTIFIER_FIELDS:
      if field in record:
        identifier = f"{field}={record[field]}"
        break
  return f"{relative_path}[{index}] ({identifier})"


def validate_record(
  relative_path: Path, index: int, record: object, schema: dict[str, type], errors: list[str]
) -> None:
  if not isinstance(record, dict):
    errors.append(f"{relative_path}[{index}]: expected object")
    return
  label = record_label(relative_path, index, record)
  for field, expected_type in schema.items():
    if field not in record:
      errors.append(f"{label}: missing required field '{field}'")
      continue
    value = record[field]
    if type(value) is not expected_type:
      expected_name = "integer" if expected_type is int else expected_type.__name__
      article = "an" if expected_name == "integer" else "a"
      errors.append(f"{label}: field '{field}' must be {article} {expected_name}")
      continue
    if field in CODE_WIDTHS:
      validate_code_width(label, field, value, errors)
    if expected_type is str and not value.strip():
      errors.append(f"{label}: field '{field}' must be a non-empty string")
    if field == "postalCode" and not 10000 <= value <= 99999:
      errors.append(f"{label}: field 'postalCode' must be a five-digit integer")


def load_json(root: Path, relative_path: Path, errors: list[str]) -> Any:
  try:
    return json.loads(
      read_json_file(root, relative_path),
      object_pairs_hook=reject_duplicate_json_keys,
      parse_constant=reject_nonfinite_json_constant,
    )
  except SymbolicLinkJsonFileError:
    errors.append(f"{relative_path}: symbolic links are not allowed")
    return None
  except NonRegularJsonFileError:
    errors.append(f"{relative_path}: must be a regular file")
    return None
  except OversizedJsonFileError:
    errors.append(f"{relative_path}: file exceeds {MAX_JSON_BYTES} byte limit")
    return None
  except InvalidJsonConstantError as error:
    errors.append(f"{relative_path}: invalid JSON constant {error.constant!r}")
    return None
  except DuplicateJsonKeyError as error:
    errors.append(f"{relative_path}: duplicate JSON key {error.key!r}")
    return None
  except UnicodeDecodeError:
    errors.append(f"{relative_path}: invalid UTF-8")
    return None
  except RecursionError:
    errors.append(f"{relative_path}: invalid JSON: nesting too deep")
    return None
  except (OSError, json.JSONDecodeError) as error:
    errors.append(f"{relative_path}: invalid JSON: {error}")
    return None
  except ValueError:
    errors.append(f"{relative_path}: invalid JSON: integer too large")
    return None


def validate_repository(root: Path) -> list[str]:
  """Return all JSON parsing errors for the repository rooted at *root*."""
  errors: list[str] = []
  src_paths = sorted(discover_src_json_paths(root, errors), key=str)
  relative_paths = dict.fromkeys((*DATA_PATHS, *src_paths))
  datasets = {
    str(relative_path): load_json(root, relative_path, errors)
    for relative_path in relative_paths
  }
  if datasets["package.json"] is not None and not isinstance(datasets["package.json"], dict):
    errors.append("package.json: expected object")
  for relative_path, schema in RECORD_SCHEMAS.items():
    data = datasets[relative_path]
    if not isinstance(data, list):
      errors.append(f"{relative_path}: expected list")
      continue
    if not data:
      errors.append(f"{relative_path}: expected a non-empty list")
      continue
    for index, record in enumerate(data):
      validate_record(Path(relative_path), index, record, schema, errors)
  for relative_path, fields in UNIQUE_FIELDS.items():
    validate_unique_fields(relative_path, datasets[relative_path], fields, errors)
  for relative_path in ("src/subdistricts.json", "src/geography.json"):
    records = datasets[relative_path]
    if isinstance(records, list):
      for index, record in enumerate(records):
        if isinstance(record, dict):
          validate_postal_codes(relative_path, index, record, errors)
  validate_foreign_keys(datasets, errors)
  validate_geography_subdistrict_keys(datasets, errors)
  validate_multi_postal(datasets, errors)
  return errors


def main() -> int:
  errors = validate_repository(Path(__file__).resolve().parents[1])
  if errors:
    print("Data validation failed:")
    print("\n".join(f"- {error}" for error in errors))
    return 1
  print("Data validation passed.")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
