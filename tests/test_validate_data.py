from __future__ import annotations

from pathlib import Path
import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

from scripts.validate_data import validate_repository


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = ROOT / ".github/workflows/validate-data.yml"


class ValidateRepositoryTests(unittest.TestCase):
    def test_current_repository_data_parses_without_errors(self) -> None:
        self.assertEqual([], validate_repository(ROOT))

    def test_reports_non_object_package_json_root(self) -> None:
        fixture_root = self.fixture_root()
        (fixture_root / "package.json").write_text("[]", encoding="utf-8")

        errors = validate_repository(fixture_root)

        self.assertEqual(["package.json: expected object"], errors)

    def test_reports_invalid_package_json_with_relative_path(self) -> None:
        fixture_root = self.fixture_root()
        (fixture_root / "package.json").write_text("{", encoding="utf-8")

        errors = validate_repository(fixture_root)

        self.assertEqual(1, len(errors))
        self.assertTrue(errors[0].startswith("package.json: invalid JSON:"))

    def test_readme_documents_validation_commands(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("python3 -m unittest discover -s tests -v", readme)
        self.assertIn("python3 scripts/validate_data.py", readme)

    def test_workflow_runs_validation_for_pull_requests_and_merge_groups(self) -> None:
        self.assertTrue(WORKFLOW_PATH.is_file())
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

        self.assertIn("pull_request:\n    branches: [main]", workflow)
        self.assertIn("merge_group:", workflow)
        self.assertIn("contents: read", workflow)
        self.assertIn("validate-data:", workflow)
        self.assertIn("timeout-minutes: 5", workflow)
        self.assertIn("actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683", workflow)
        self.assertIn("ref: ${{ github.sha }}", workflow)
        self.assertIn("python3 -m unittest discover -s tests -v", workflow)
        self.assertIn("python3 scripts/validate_data.py", workflow)
        self.assertNotIn("pull_request_target", workflow)
        self.assertNotIn("paths:", workflow)
        self.assertNotIn("secrets", workflow)

    def test_workflow_emits_nonblocking_pull_request_data_summary(self) -> None:
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

        self.assertIn("fetch-depth: 0", workflow)
        self.assertIn("name: Summarize dataset data changes", workflow)
        self.assertIn("if: github.event_name == 'pull_request'", workflow)
        self.assertIn("continue-on-error: true", workflow)
        self.assertIn("BASE_SHA: ${{ github.event.pull_request.base.sha }}", workflow)
        self.assertIn("CANDIDATE_SHA: ${{ github.sha }}", workflow)
        self.assertIn('python3 scripts/summarize_data_changes.py --base-sha "$BASE_SHA"', workflow)
        self.assertIn('--head-sha "$CANDIDATE_SHA" >> "$GITHUB_STEP_SUMMARY"', workflow)

    def test_reports_unhashable_invalid_code_without_crashing(self) -> None:
        fixture_root = self.fixture_root()
        provinces_path = fixture_root / "src/provinces.json"
        provinces = json.loads(provinces_path.read_text(encoding="utf-8"))
        provinces[0]["id"] = []
        provinces_path.write_text(json.dumps(provinces), encoding="utf-8")

        errors = validate_repository(fixture_root)

        self.assertIn(
            "src/provinces.json[0] (provinceCode=10): field 'id' must be an integer",
            errors,
        )

    def test_reports_empty_canonical_datasets_without_cardinality_checks(self) -> None:
        fixture_root = self.fixture_root()
        for filename in (
            "provinces.json",
            "districts.json",
            "subdistricts.json",
            "geography.json",
        ):
            (fixture_root / "src" / filename).write_text("[]", encoding="utf-8")

        errors = validate_repository(fixture_root)

        for filename in (
            "provinces.json",
            "districts.json",
            "subdistricts.json",
            "geography.json",
        ):
            self.assertIn(f"src/{filename}: expected a non-empty list", errors)

    def test_reports_missing_required_field_with_path_and_identifier(self) -> None:
        fixture_root = self.fixture_root()
        provinces_path = fixture_root / "src/provinces.json"
        provinces = json.loads(provinces_path.read_text(encoding="utf-8"))
        del provinces[0]["provinceNameEn"]
        provinces_path.write_text(json.dumps(provinces), encoding="utf-8")

        errors = validate_repository(fixture_root)

        self.assertIn(
            "src/provinces.json[0] (provinceCode=10): missing required field "
            "'provinceNameEn'",
            errors,
        )

    def test_reports_scalar_type_format_and_empty_name_errors(self) -> None:
        fixture_root = self.fixture_root()
        changes = (
            ("provinces.json", "provinceCode", "10"),
            ("districts.json", "postalCode", 1234),
            ("subdistricts.json", "subdistrictNameTh", " "),
            ("geography.json", "provinceNameEn", ""),
        )
        for filename, field, value in changes:
            path = fixture_root / "src" / filename
            records = json.loads(path.read_text(encoding="utf-8"))
            records[0][field] = value
            path.write_text(json.dumps(records), encoding="utf-8")

        errors = validate_repository(fixture_root)

        self.assertIn(
            "src/provinces.json[0] (provinceCode=10): field 'provinceCode' "
            "must be an integer",
            errors,
        )
        self.assertIn(
            "src/districts.json[0] (districtCode=1001): field 'postalCode' "
            "must be a five-digit integer",
            errors,
        )
        self.assertIn(
            "src/subdistricts.json[0] (subdistrictCode=100101): field "
            "'subdistrictNameTh' must be a non-empty string",
            errors,
        )
        self.assertIn(
            "src/geography.json[0] (subdistrictCode=100101): field "
            "'provinceNameEn' must be a non-empty string",
            errors,
        )

    def test_reports_duplicate_keys_foreign_key_and_geography_join_mismatches(self) -> None:
        fixture_root = self.fixture_root()
        provinces_path = fixture_root / "src/provinces.json"
        provinces = json.loads(provinces_path.read_text(encoding="utf-8"))
        provinces[1]["id"] = provinces[0]["id"]
        provinces_path.write_text(json.dumps(provinces), encoding="utf-8")

        districts_path = fixture_root / "src/districts.json"
        districts = json.loads(districts_path.read_text(encoding="utf-8"))
        districts[0]["provinceCode"] = 999
        districts_path.write_text(json.dumps(districts), encoding="utf-8")

        subdistricts_path = fixture_root / "src/subdistricts.json"
        subdistricts = json.loads(subdistricts_path.read_text(encoding="utf-8"))
        subdistricts[0]["provinceCode"] = 11
        subdistricts_path.write_text(json.dumps(subdistricts), encoding="utf-8")

        geography_path = fixture_root / "src/geography.json"
        geography = json.loads(geography_path.read_text(encoding="utf-8"))
        geography[0]["provinceNameEn"] = "Incorrect"
        geography_path.write_text(json.dumps(geography), encoding="utf-8")

        errors = validate_repository(fixture_root)

        self.assertIn("src/provinces.json: duplicate id 1 at records 0 and 1", errors)
        self.assertIn(
            "src/districts.json[0] (districtCode=1001): unknown provinceCode 999",
            errors,
        )
        self.assertIn(
            "src/subdistricts.json[0] (subdistrictCode=100101): provinceCode 11 does not match "
            "src/districts.json (districtCode=1001)",
            errors,
        )
        self.assertIn(
            "src/geography.json[0] (subdistrictCode=100101): field 'provinceNameEn' "
            "does not match src/provinces.json (provinceCode=10)",
            errors,
        )

    def test_reports_invalid_code_widths_after_coordinated_changes(self) -> None:
        fixture_root = self.fixture_root()

        def replace_code(filename, field, old, new, entries_key=None):
            path = fixture_root / "src" / filename
            data = json.loads(path.read_text(encoding="utf-8"))
            records = data[entries_key] if entries_key else data
            for record in records:
                if record.get(field) == old:
                    record[field] = new
            path.write_text(json.dumps(data), encoding="utf-8")

        for filename, entries_key in (
            ("provinces.json", None),
            ("districts.json", None),
            ("subdistricts.json", None),
            ("geography.json", None),
            ("multi-postal-codes.json", "subdistricts"),
        ):
            replace_code(filename, "provinceCode", 10, 1, entries_key)
        for filename, entries_key in (
            ("districts.json", None),
            ("subdistricts.json", None),
            ("geography.json", None),
            ("multi-postal-codes.json", "subdistricts"),
        ):
            replace_code(filename, "districtCode", 1001, 101, entries_key)
        for filename, entries_key in (
            ("subdistricts.json", None),
            ("geography.json", None),
            ("multi-postal-codes.json", "subdistricts"),
        ):
            replace_code(filename, "subdistrictCode", 100101, 10001, entries_key)

        errors = validate_repository(fixture_root)

        self.assertIn(
            "src/provinces.json[0] (provinceCode=1): field 'provinceCode' "
            "must be a two-digit integer",
            errors,
        )
        self.assertIn(
            "src/districts.json[0] (districtCode=101): field 'districtCode' "
            "must be a four-digit integer",
            errors,
        )
        self.assertIn(
            "src/subdistricts.json[0] (subdistrictCode=10001): field "
            "'subdistrictCode' must be a six-digit integer",
            errors,
        )
        self.assertIn(
            "src/geography.json[0] (subdistrictCode=10001): field "
            "'subdistrictCode' must be a six-digit integer",
            errors,
        )

    def test_reports_invalid_code_width_in_multi_postal_audit(self) -> None:
        fixture_root = self.fixture_root()
        multi_path = fixture_root / "src/multi-postal-codes.json"
        multi = json.loads(multi_path.read_text(encoding="utf-8"))
        multi["subdistricts"][0]["provinceCode"] = 1
        multi_path.write_text(json.dumps(multi), encoding="utf-8")

        errors = validate_repository(fixture_root)

        self.assertIn(
            "src/multi-postal-codes.json[0] (subdistrictCode=100508): field "
            "'provinceCode' must be a two-digit integer",
            errors,
        )

    def test_reports_geography_id_mismatch_with_subdistrict(self) -> None:
        fixture_root = self.fixture_root()
        geography_path = fixture_root / "src/geography.json"
        geography = json.loads(geography_path.read_text(encoding="utf-8"))
        geography[0]["id"] = 999999
        geography_path.write_text(json.dumps(geography), encoding="utf-8")

        errors = validate_repository(fixture_root)

        self.assertIn(
            "src/geography.json[0] (subdistrictCode=100101): field 'id' does not match "
            "src/subdistricts.json (subdistrictCode=100101)",
            errors,
        )

    def test_reports_missing_subdistrict_from_geography(self) -> None:
        fixture_root = self.fixture_root()
        geography_path = fixture_root / "src/geography.json"
        geography = json.loads(geography_path.read_text(encoding="utf-8"))
        geography = [
            record for record in geography if record["subdistrictCode"] != 100101
        ]
        geography_path.write_text(json.dumps(geography), encoding="utf-8")

        errors = validate_repository(fixture_root)

        self.assertIn(
            "src/geography.json: subdistrictCode set does not match "
            "src/subdistricts.json (missing=[100101], unexpected=[])",
            errors,
        )

    def test_reports_unexpected_subdistrict_in_geography(self) -> None:
        fixture_root = self.fixture_root()
        geography_path = fixture_root / "src/geography.json"
        geography = json.loads(geography_path.read_text(encoding="utf-8"))
        extra = dict(geography[0])
        extra["id"] = 999999
        extra["subdistrictCode"] = 999999
        geography.append(extra)
        geography_path.write_text(json.dumps(geography), encoding="utf-8")

        errors = validate_repository(fixture_root)

        self.assertIn(
            "src/geography.json: subdistrictCode set does not match "
            "src/subdistricts.json (missing=[], unexpected=[999999])",
            errors,
        )

    def test_reports_duplicate_multi_postal_audit_entry(self) -> None:
        fixture_root = self.fixture_root()
        multi_path = fixture_root / "src/multi-postal-codes.json"
        multi = json.loads(multi_path.read_text(encoding="utf-8"))
        duplicate_index = len(multi["subdistricts"])
        multi["subdistricts"].append(dict(multi["subdistricts"][0]))
        multi["count"] = len(multi["subdistricts"])
        multi_path.write_text(json.dumps(multi), encoding="utf-8")

        errors = validate_repository(fixture_root)

        self.assertIn(
            "src/multi-postal-codes.json: duplicate subdistrictCode 100508 "
            f"at entries 0 and {duplicate_index}",
            errors,
        )

    def test_reports_all_unhashable_foreign_and_audit_identifiers(self) -> None:
        cases = (
            ("districts.json", None, "provinceCode"),
            ("subdistricts.json", None, "provinceCode"),
            ("subdistricts.json", None, "districtCode"),
            ("geography.json", None, "provinceCode"),
            ("geography.json", None, "districtCode"),
            ("geography.json", None, "subdistrictCode"),
            ("multi-postal-codes.json", "subdistricts", "provinceCode"),
            ("multi-postal-codes.json", "subdistricts", "districtCode"),
            ("multi-postal-codes.json", "subdistricts", "subdistrictCode"),
        )
        for filename, entries_key, field in cases:
            with self.subTest(filename=filename, field=field):
                fixture_root = self.fixture_root()
                path = fixture_root / "src" / filename
                data = json.loads(path.read_text(encoding="utf-8"))
                records = data[entries_key] if entries_key else data
                records[0][field] = []
                path.write_text(json.dumps(data), encoding="utf-8")

                errors = validate_repository(fixture_root)

                self.assertTrue(
                    any(f"field '{field}' must be" in error for error in errors),
                    errors,
                )

    def test_reports_unhashable_audit_key_without_crashing(self) -> None:
        fixture_root = self.fixture_root()
        multi_path = fixture_root / "src/multi-postal-codes.json"
        multi = json.loads(multi_path.read_text(encoding="utf-8"))
        multi["subdistricts"][0]["subdistrictCode"] = []
        multi_path.write_text(json.dumps(multi), encoding="utf-8")

        errors = validate_repository(fixture_root)

        self.assertIn(
            "src/multi-postal-codes.json[0] (subdistrictCode=[]): field "
            "'subdistrictCode' must be a integer",
            errors,
        )

    def test_reports_unhashable_foreign_key_without_crashing(self) -> None:
        fixture_root = self.fixture_root()
        districts_path = fixture_root / "src/districts.json"
        districts = json.loads(districts_path.read_text(encoding="utf-8"))
        districts[0]["provinceCode"] = []
        districts_path.write_text(json.dumps(districts), encoding="utf-8")

        errors = validate_repository(fixture_root)

        self.assertIn(
            "src/districts.json[0] (districtCode=1001): field 'provinceCode' "
            "must be an integer",
            errors,
        )

    def test_reports_unhashable_index_key_without_crashing(self) -> None:
        fixture_root = self.fixture_root()
        provinces_path = fixture_root / "src/provinces.json"
        provinces = json.loads(provinces_path.read_text(encoding="utf-8"))
        provinces[0]["provinceCode"] = []
        provinces_path.write_text(json.dumps(provinces), encoding="utf-8")

        errors = validate_repository(fixture_root)

        self.assertIn(
            "src/provinces.json[0] (provinceCode=[]): field 'provinceCode' "
            "must be an integer",
            errors,
        )

    def test_reports_unhashable_geography_key_without_crashing(self) -> None:
        fixture_root = self.fixture_root()
        geography_path = fixture_root / "src/geography.json"
        geography = json.loads(geography_path.read_text(encoding="utf-8"))
        geography[0]["subdistrictCode"] = []
        geography_path.write_text(json.dumps(geography), encoding="utf-8")

        errors = validate_repository(fixture_root)

        self.assertIn(
            "src/geography.json[0] (subdistrictCode=[]): field 'subdistrictCode' "
            "must be an integer",
            errors,
        )

    def test_reports_duplicate_json_object_key(self) -> None:
        fixture_root = self.fixture_root()
        (fixture_root / "src/extra.json").write_text(
            '{"first": 1, "first": 2}', encoding="utf-8"
        )

        errors = validate_repository(fixture_root)

        self.assertEqual(["src/extra.json: duplicate JSON key 'first'"], errors)

    def test_rejects_nonfinite_json_constants_in_every_parsed_path(self) -> None:
        relative_paths = (
            "package.json",
            "src/provinces.json",
            "src/districts.json",
            "src/subdistricts.json",
            "src/geography.json",
            "src/multi-postal-codes.json",
            "src/extra.json",
        )
        for constant in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(constant=constant):
                fixture_root = self.fixture_root()
                for relative_path in relative_paths:
                    (fixture_root / relative_path).write_text(constant, encoding="utf-8")

                errors = validate_repository(fixture_root)

                for relative_path in relative_paths:
                    self.assertIn(
                        f"{relative_path}: invalid JSON constant {constant!r}",
                        errors,
                    )

    def test_reports_deeply_nested_json_as_a_diagnostic(self) -> None:
        fixture_root = self.fixture_root()
        (fixture_root / "src/extra.json").write_text("[" * 10000 + "]" * 10000, encoding="utf-8")

        errors = validate_repository(fixture_root)

        self.assertEqual(["src/extra.json: invalid JSON: nesting too deep"], errors)

    def test_reports_oversized_json_integer_as_a_diagnostic(self) -> None:
        fixture_root = self.fixture_root()
        (fixture_root / "src/extra.json").write_text(
            '{"value": ' + "1" * 5000 + "}", encoding="utf-8"
        )

        errors = validate_repository(fixture_root)

        self.assertEqual(["src/extra.json: invalid JSON: integer too large"], errors)

    def test_reports_invalid_utf8_json_file(self) -> None:
        fixture_root = self.fixture_root()
        (fixture_root / "src/extra.json").write_bytes(b"\xff")

        errors = validate_repository(fixture_root)

        self.assertEqual(
            ["src/extra.json: invalid UTF-8"],
            errors,
        )

    def test_reports_invalid_extra_json_file_in_src(self) -> None:
        fixture_root = self.fixture_root()
        (fixture_root / "src/extra.json").write_text("{", encoding="utf-8")

        errors = validate_repository(fixture_root)

        self.assertEqual(1, len(errors))
        self.assertTrue(errors[0].startswith("src/extra.json: invalid JSON:"))

    def test_rejects_symlinked_json_file_without_reading_target(self) -> None:
        fixture_root = self.fixture_root()
        (fixture_root / "src/extra.json").symlink_to("/dev/zero")

        errors = validate_repository(fixture_root)

        self.assertEqual(["src/extra.json: symbolic links are not allowed"], errors)

    def test_rejects_symlinked_canonical_package_json(self) -> None:
        fixture_root = self.fixture_root()
        package_path = fixture_root / "package.json"
        package_path.unlink()
        package_path.symlink_to("src/provinces.json")

        errors = validate_repository(fixture_root)

        self.assertEqual(["package.json: symbolic links are not allowed"], errors)

    def test_rejects_symlinked_src_directory(self) -> None:
        fixture_root = self.fixture_root()
        source_directory = fixture_root / "source-data"
        (fixture_root / "src").rename(source_directory)
        (fixture_root / "src").symlink_to(source_directory, target_is_directory=True)

        errors = validate_repository(fixture_root)

        self.assertIn("src: symbolic links are not allowed", errors)

    def test_rejects_symlinked_parent_directory_for_nested_json(self) -> None:
        fixture_root = self.fixture_root()
        nested_target = fixture_root / "nested-target"
        nested_target.mkdir()
        (nested_target / "extra.json").write_text("{}", encoding="utf-8")
        (fixture_root / "src" / "nested").symlink_to(nested_target, target_is_directory=True)

        errors = validate_repository(fixture_root)

        self.assertIn("src/nested: symbolic links are not allowed", errors)

    def test_rejects_fifo_swapped_after_lstat_without_blocking(self) -> None:
        fixture_root = self.fixture_root()
        race_path = fixture_root / "src" / "race.json"
        race_path.write_text("{}", encoding="utf-8")
        real_open = os.open

        def swap_to_fifo(path, flags, *args, **kwargs):
            if Path(path).name == "race.json":
                race_path.unlink()
                os.mkfifo(race_path)
                self.assertTrue(flags & os.O_NONBLOCK)
            return real_open(path, flags, *args, **kwargs)

        with mock.patch("scripts.validate_data.os.open", side_effect=swap_to_fifo):
            errors = validate_repository(fixture_root)

        self.assertIn("src/race.json: must be a regular file", errors)

    def test_rejects_non_regular_json_file(self) -> None:
        fixture_root = self.fixture_root()
        (fixture_root / "src/extra.json").mkdir()

        errors = validate_repository(fixture_root)

        self.assertEqual(["src/extra.json: must be a regular file"], errors)

    def test_rejects_json_file_larger_than_read_limit(self) -> None:
        fixture_root = self.fixture_root()
        oversized_path = fixture_root / "src/extra.json"
        with oversized_path.open("wb") as file:
            file.truncate(16 * 1024 * 1024 + 1)

        errors = validate_repository(fixture_root)

        self.assertEqual(["src/extra.json: file exceeds 16777216 byte limit"], errors)

    def test_reports_invalid_data_root_types(self) -> None:
        fixture_root = self.fixture_root()
        for filename in (
            "provinces.json",
            "districts.json",
            "subdistricts.json",
            "geography.json",
        ):
            (fixture_root / "src" / filename).write_text("{}", encoding="utf-8")
        (fixture_root / "src/multi-postal-codes.json").write_text("[]", encoding="utf-8")

        errors = validate_repository(fixture_root)

        for filename in (
            "provinces.json",
            "districts.json",
            "subdistricts.json",
            "geography.json",
        ):
            self.assertIn(f"src/{filename}: expected list", errors)
        self.assertIn("src/multi-postal-codes.json: expected object", errors)

    def test_reports_postal_code_list_and_multi_postal_audit_errors(self) -> None:
        fixture_root = self.fixture_root()
        subdistricts_path = fixture_root / "src/subdistricts.json"
        subdistricts = json.loads(subdistricts_path.read_text(encoding="utf-8"))
        subdistricts[0]["postalCodes"] = [
            {"postalCode": 9999, "isPrimary": False, "detailTh": "", "detailEn": 7},
            {"postalCode": 9999, "isPrimary": False, "detailTh": "Other", "detailEn": "Other"},
        ]
        subdistricts[1]["postalCodes"] = [
            {"postalCode": 10201, "isPrimary": True, "detailTh": "Primary", "detailEn": "Primary"},
            {"postalCode": 10202, "isPrimary": False, "detailTh": "Other", "detailEn": "Other"},
        ]
        subdistricts_path.write_text(json.dumps(subdistricts), encoding="utf-8")

        multi_path = fixture_root / "src/multi-postal-codes.json"
        multi = json.loads(multi_path.read_text(encoding="utf-8"))
        multi["count"] = 85
        multi["source"]["title"] = " "
        multi["subdistricts"][0]["postalCodes"][1]["detailEn"] = "Wrong"
        multi_path.write_text(json.dumps(multi), encoding="utf-8")

        errors = validate_repository(fixture_root)

        self.assertIn(
            "src/subdistricts.json[0] (subdistrictCode=100101): postalCodes[0] must be primary",
            errors,
        )
        self.assertIn(
            "src/subdistricts.json[0] (subdistrictCode=100101): postalCodes must have exactly one primary entry",
            errors,
        )
        self.assertIn(
            "src/subdistricts.json[0] (subdistrictCode=100101): postalCodes[0].postalCode must be a five-digit integer",
            errors,
        )
        self.assertIn(
            "src/subdistricts.json[0] (subdistrictCode=100101): duplicate postal code 9999",
            errors,
        )
        self.assertIn(
            "src/subdistricts.json[1] (subdistrictCode=100102): primary postal code 10201 does not match postalCode 10200",
            errors,
        )
        self.assertIn(
            "src/multi-postal-codes.json: source.title must be a non-empty string",
            errors,
        )
        self.assertIn(
            "src/multi-postal-codes.json: count 85 does not match subdistricts length 86",
            errors,
        )
        self.assertIn(
            "src/multi-postal-codes.json[0] (subdistrictCode=100508): postalCodes does not match src/subdistricts.json",
            errors,
        )

    def fixture_root(self):
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        fixture_root = Path(temporary_directory.name)
        shutil.copy2(ROOT / "package.json", fixture_root / "package.json")
        shutil.copytree(ROOT / "src", fixture_root / "src")
        return fixture_root


if __name__ == "__main__":
    unittest.main()
