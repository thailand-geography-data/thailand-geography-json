from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.summarize_data_changes import (
    DATASET_PATHS,
    compare_directory_datasets,
    compare_git_revisions,
    render_summary,
)


ROOT = Path(__file__).resolve().parents[1]


class DataChangeSummaryTests(unittest.TestCase):
    def test_reports_additions_removals_field_changes_and_postal_list_deltas(self) -> None:
        base_root, candidate_root = self.fixture_roots(
            {
                "src/provinces.json": [
                    {
                        "id": 1,
                        "provinceCode": 10,
                        "provinceNameTh": "เดิม",
                        "provinceNameEn": "Old",
                    },
                    {
                        "id": 3,
                        "provinceCode": 30,
                        "provinceNameTh": "ลบ",
                        "provinceNameEn": "Removed",
                    },
                ],
                "src/subdistricts.json": [
                    {
                        "id": 5,
                        "provinceCode": 10,
                        "districtCode": 1001,
                        "subdistrictCode": 100101,
                        "subdistrictNameTh": "เดิม",
                        "subdistrictNameEn": "Old",
                        "postalCode": 10100,
                        "postalCodes": [{"postalCode": 10100}],
                    },
                    {
                        "id": 6,
                        "provinceCode": 10,
                        "districtCode": 1002,
                        "subdistrictCode": 100201,
                        "subdistrictNameTh": "ลด",
                        "subdistrictNameEn": "Reduced",
                        "postalCode": 10200,
                        "postalCodes": [
                            {"postalCode": 10200},
                            {"postalCode": 10201},
                        ],
                    },
                    {
                        "id": 8,
                        "provinceCode": 10,
                        "districtCode": 1003,
                        "subdistrictCode": 100301,
                        "subdistrictNameTh": "เพิ่มรายการ",
                        "subdistrictNameEn": "Added list",
                        "postalCode": 10300,
                    },
                ],
            },
            {
                "src/provinces.json": [
                    {
                        "id": 1,
                        "provinceCode": 11,
                        "provinceNameTh": "ใหม่",
                        "provinceNameEn": "New",
                    },
                    {
                        "id": 2,
                        "provinceCode": 20,
                        "provinceNameTh": "เพิ่ม",
                        "provinceNameEn": "Added",
                    },
                ],
                "src/subdistricts.json": [
                    {
                        "id": 5,
                        "provinceCode": 10,
                        "districtCode": 1001,
                        "subdistrictCode": 100102,
                        "subdistrictNameTh": "ใหม่",
                        "subdistrictNameEn": "New",
                        "postalCode": 10200,
                        "postalCodes": [
                            {"postalCode": 10200},
                            {"postalCode": 10201},
                            {"postalCode": 10202},
                        ],
                    },
                    {
                        "id": 7,
                        "provinceCode": 10,
                        "districtCode": 1002,
                        "subdistrictCode": 100201,
                        "subdistrictNameTh": "ลด",
                        "subdistrictNameEn": "Reduced",
                        "postalCode": 10200,
                        "postalCodes": [{"postalCode": 10200}],
                    },
                    {
                        "id": 8,
                        "provinceCode": 10,
                        "districtCode": 1003,
                        "subdistrictCode": 100301,
                        "subdistrictNameTh": "เพิ่มรายการ",
                        "subdistrictNameEn": "Added list",
                        "postalCode": 10300,
                        "postalCodes": [{"postalCode": 10300}],
                    },
                ],
            },
        )

        summary = compare_directory_datasets(base_root, candidate_root)
        provinces = summary["src/provinces.json"]
        subdistricts = summary["src/subdistricts.json"]

        self.assertEqual(1, provinces.added)
        self.assertEqual(1, provinces.removed)
        self.assertEqual(
            {
                "id": 0,
                "geographic_codes": 1,
                "thai_names": 1,
                "english_names": 1,
                "postalCode": 0,
            },
            provinces.field_changes,
        )
        self.assertEqual(
            [("id=1", "provinceCode: 10 → 11")],
            provinces.changed_geographic_identifiers,
        )
        self.assertEqual(1, subdistricts.field_changes["id"])
        self.assertEqual(1, subdistricts.field_changes["geographic_codes"])
        self.assertEqual(1, subdistricts.field_changes["thai_names"])
        self.assertEqual(1, subdistricts.field_changes["english_names"])
        self.assertEqual(1, subdistricts.field_changes["postalCode"])
        self.assertEqual((3, 1, 3), subdistricts.postal_codes_delta)

        output = render_summary(summary)
        self.assertIn("### src/provinces.json", output)
        self.assertIn("- Records: 1 added, 1 removed", output)
        self.assertIn("- Changed geographical identifiers: id=1 (provinceCode: 10 → 11)", output)
        self.assertIn("### src/subdistricts.json", output)
        self.assertIn("- postalCodes entries: +3 / -1 across 3 changed lists", output)

    def test_does_not_pair_ambiguous_records_with_crossed_ids_and_geographic_codes(self) -> None:
        base_root, candidate_root = self.fixture_roots(
            {
                "src/provinces.json": [
                    {"id": 1, "provinceCode": 10, "provinceNameTh": "A", "provinceNameEn": "A"},
                    {"id": 2, "provinceCode": 11, "provinceNameTh": "B", "provinceNameEn": "B"},
                ]
            },
            {
                "src/provinces.json": [
                    {"id": 1, "provinceCode": 11, "provinceNameTh": "A", "provinceNameEn": "A"},
                    {"id": 2, "provinceCode": 10, "provinceNameTh": "B", "provinceNameEn": "B"},
                ]
            },
        )

        provinces = compare_directory_datasets(base_root, candidate_root)["src/provinces.json"]

        self.assertEqual(2, provinces.added)
        self.assertEqual(2, provinces.removed)
        self.assertTrue(all(count == 0 for count in provinces.field_changes.values()))
        self.assertEqual([], provinces.changed_geographic_identifiers)

    def test_compares_current_repository_history_and_cli_output(self) -> None:
        base_sha = self.git("rev-parse", "HEAD^")
        head_sha = self.git("rev-parse", "HEAD")

        summary = compare_git_revisions(ROOT, base_sha, head_sha)
        completed = subprocess.run(
            [
                sys.executable,
                "scripts/summarize_data_changes.py",
                "--base-sha",
                base_sha,
                "--head-sha",
                head_sha,
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(set(DATASET_PATHS), set(summary))
        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertIn("## Dataset data changes", completed.stdout)
        for dataset_path in DATASET_PATHS:
            self.assertIn(f"### {dataset_path}", completed.stdout)

    def fixture_roots(self, base_overrides, candidate_overrides):
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        root = Path(temporary_directory.name)
        base_root = root / "base"
        candidate_root = root / "candidate"
        for fixture_root, overrides in (
            (base_root, base_overrides),
            (candidate_root, candidate_overrides),
        ):
            for dataset_path in DATASET_PATHS:
                data = overrides.get(dataset_path, self.empty_dataset(dataset_path))
                path = fixture_root / dataset_path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(data), encoding="utf-8")
        return base_root, candidate_root

    @staticmethod
    def empty_dataset(dataset_path):
        if dataset_path == "src/multi-postal-codes.json":
            return {"subdistricts": []}
        return []

    @staticmethod
    def git(*args):
        return subprocess.run(
            ["git", *args],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()


if __name__ == "__main__":
    unittest.main()
