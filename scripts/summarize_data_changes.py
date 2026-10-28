#!/usr/bin/env python3
"""Render an informational summary of data changes between two revisions."""

from __future__ import annotations

from dataclasses import dataclass
import argparse
import json
from pathlib import Path
import re
import subprocess
from typing import Any


DATASET_PATHS = (
    "src/provinces.json",
    "src/districts.json",
    "src/subdistricts.json",
    "src/geography.json",
    "src/multi-postal-codes.json",
    "src/regions.json",
)


@dataclass(frozen=True)
class DatasetChangeSummary:
    added: int
    removed: int
    field_changes: dict[str, int]
    postal_codes_delta: tuple[int, int, int]
    changed_geographic_identifiers: list[tuple[str, str]]
    region_province_codes_delta: tuple[int, int, int] = (0, 0, 0)


def records(data: Any, path: str) -> list[dict[str, Any]]:
    if path == "src/multi-postal-codes.json":
        data = data["subdistricts"]
    return data


def geographic_fields_for(path: str) -> tuple[str, ...]:
    if path == "src/provinces.json":
        return ("provinceCode",)
    if path == "src/districts.json":
        return ("provinceCode", "districtCode")
    if path == "src/regions.json":
        return ("regionCode",)
    return ("provinceCode", "districtCode", "subdistrictCode")


def unique_indexes(records, field):
    indexes = {}
    duplicate_values = set()
    for index, record in enumerate(records):
        value = record.get(field)
        if value is None:
            continue
        try:
            hash(value)
        except TypeError:
            continue
        if value in indexes:
            duplicate_values.add(value)
        else:
            indexes[value] = index
    return {value: index for value, index in indexes.items() if value not in duplicate_values}


def safely_pair_records(base_records, candidate_records, fields):
    """Return only isolated one-to-one id/code match components."""
    adjacency = {}
    for field in ("id", *fields):
        base_indexes = unique_indexes(base_records, field)
        candidate_indexes = unique_indexes(candidate_records, field)
        for value in base_indexes.keys() & candidate_indexes.keys():
            base_node = ("base", base_indexes[value])
            candidate_node = ("candidate", candidate_indexes[value])
            adjacency.setdefault(base_node, set()).add(candidate_node)
            adjacency.setdefault(candidate_node, set()).add(base_node)
    pairs = []
    visited = set()
    for node in adjacency:
        if node in visited:
            continue
        component = set()
        pending = [node]
        visited.add(node)
        while pending:
            current = pending.pop()
            component.add(current)
            for neighbour in adjacency[current]:
                if neighbour not in visited:
                    visited.add(neighbour)
                    pending.append(neighbour)
        base_nodes = [item for item in component if item[0] == "base"]
        candidate_nodes = [item for item in component if item[0] == "candidate"]
        if len(base_nodes) == len(candidate_nodes) == 1:
            pairs.append((base_nodes[0][1], candidate_nodes[0][1]))
    return pairs


def annotation_identifier(base_record, candidate_record, code_fields) -> str:
    """Label an annotation by `id` when the record has one, else its first geographic code."""
    if "id" in base_record or "id" in candidate_record:
        if base_record.get("id") == candidate_record.get("id"):
            return f"id={base_record.get('id')}"
        return f"id={base_record.get('id')} → {candidate_record.get('id')}"
    for field in code_fields:
        if field in base_record or field in candidate_record:
            value = base_record[field] if field in base_record else candidate_record[field]
            return f"{field}={value}"
    return "unknown record"


def compare_records(base_records, candidate_records, path: str) -> DatasetChangeSummary:
    code_fields = geographic_fields_for(path)
    pairs = safely_pair_records(base_records, candidate_records, code_fields)
    paired_base = {base_index for base_index, _ in pairs}
    paired_candidate = {candidate_index for _, candidate_index in pairs}
    changed_codes = 0
    changed_ids = 0
    thai_names = 0
    english_names = 0
    postal_codes = 0
    annotations = []
    added_postal_entries = 0
    removed_postal_entries = 0
    changed_lists = 0
    added_region_provinces = 0
    removed_region_provinces = 0
    changed_region_lists = 0
    for base_index, candidate_index in pairs:
        base_record = base_records[base_index]
        candidate_record = candidate_records[candidate_index]
        geographic_fields = [
            field for field in code_fields if base_record.get(field) != candidate_record.get(field)
        ]
        changed_ids += base_record.get("id") != candidate_record.get("id")
        changed_codes += len(geographic_fields)
        thai_names += sum(
            base_record.get(field) != candidate_record.get(field)
            for field in set(base_record) | set(candidate_record)
            if field.endswith("NameTh")
        )
        english_names += sum(
            base_record.get(field) != candidate_record.get(field)
            for field in set(base_record) | set(candidate_record)
            if field.endswith("NameEn")
        )
        postal_codes += base_record.get("postalCode") != candidate_record.get("postalCode")
        if geographic_fields:
            annotations.append(
                (
                    annotation_identifier(base_record, candidate_record, code_fields),
                    ", ".join(
                        f"{field}: {base_record.get(field)} → {candidate_record.get(field)}"
                        for field in geographic_fields
                    ),
                )
            )
        if path == "src/subdistricts.json":
            base_postal_codes = base_record.get("postalCodes", [])
            candidate_postal_codes = candidate_record.get("postalCodes", [])
            if not isinstance(base_postal_codes, list) or not isinstance(candidate_postal_codes, list):
                continue
            difference = len(candidate_postal_codes) - len(base_postal_codes)
            if difference > 0:
                added_postal_entries += difference
                changed_lists += 1
            elif difference < 0:
                removed_postal_entries -= difference
                changed_lists += 1
        if path == "src/regions.json":
            base_provinces = base_record.get("provinceCodes", [])
            candidate_provinces = candidate_record.get("provinceCodes", [])
            if not isinstance(base_provinces, list) or not isinstance(candidate_provinces, list):
                continue
            try:
                base_province_set = set(base_provinces)
                candidate_province_set = set(candidate_provinces)
            except TypeError:
                continue
            added_region_provinces += len(candidate_province_set - base_province_set)
            removed_region_provinces += len(base_province_set - candidate_province_set)
            changed_region_lists += base_province_set != candidate_province_set
    return DatasetChangeSummary(
        added=len(candidate_records) - len(paired_candidate),
        removed=len(base_records) - len(paired_base),
        field_changes={
            "id": changed_ids,
            "geographic_codes": changed_codes,
            "thai_names": thai_names,
            "english_names": english_names,
            "postalCode": postal_codes,
        },
        postal_codes_delta=(added_postal_entries, removed_postal_entries, changed_lists),
        changed_geographic_identifiers=annotations,
        region_province_codes_delta=(
            added_region_provinces,
            removed_region_provinces,
            changed_region_lists,
        ),
    )


def empty_dataset(path: str):
    return {"subdistricts": []} if path == "src/multi-postal-codes.json" else []


def compare_loaded_datasets(base_datasets, candidate_datasets):
    return {
        path: compare_records(
            records(base_datasets[path], path), records(candidate_datasets[path], path), path
        )
        for path in DATASET_PATHS
    }


def compare_directory_datasets(base_root: Path, candidate_root: Path):
    base_datasets = {
        path: json.loads((base_root / path).read_text(encoding="utf-8")) for path in DATASET_PATHS
    }
    candidate_datasets = {
        path: json.loads((candidate_root / path).read_text(encoding="utf-8"))
        for path in DATASET_PATHS
    }
    return compare_loaded_datasets(base_datasets, candidate_datasets)


FULL_SHA_PATTERN = re.compile(r"[0-9a-fA-F]{40}(?:[0-9a-fA-F]{24})?\Z")


def validate_full_sha(sha: str) -> str:
    if not FULL_SHA_PATTERN.fullmatch(sha):
        raise ValueError("Git revisions must be full 40- or 64-character hexadecimal SHAs")
    return sha.lower()


def load_git_datasets(repo: Path, sha: str):
    safe_sha = validate_full_sha(sha)
    subprocess.run(
        ["git", "cat-file", "-e", f"{safe_sha}^{{commit}}"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    datasets = {}
    for path in DATASET_PATHS:
        completed = subprocess.run(
            ["git", "show", f"{safe_sha}:{path}"],
            cwd=repo,
            check=False,
            capture_output=True,
            text=True,
        )
        datasets[path] = (
            json.loads(completed.stdout) if completed.returncode == 0 else empty_dataset(path)
        )
    return datasets


def compare_git_revisions(repo: Path, base_sha: str, head_sha: str):
    return compare_loaded_datasets(
        load_git_datasets(repo, base_sha), load_git_datasets(repo, head_sha)
    )


def render_summary(summary) -> str:
    lines = ["## Dataset data changes", "", "Field counts cover safely matched records only."]
    for path in DATASET_PATHS:
        change = summary[path]
        fields = change.field_changes
        lines.extend(
            [
                "",
                f"### {path}",
                f"- Records: {change.added} added, {change.removed} removed",
                "- Changed fields: "
                f"id {fields['id']}; geographic codes {fields['geographic_codes']}; "
                f"Thai names {fields['thai_names']}; English names {fields['english_names']}; "
                f"postalCode {fields['postalCode']}",
            ]
        )
        if change.changed_geographic_identifiers:
            lines.append(
                "- Changed geographical identifiers: "
                + "; ".join(
                    f"{identifier} ({difference})"
                    for identifier, difference in change.changed_geographic_identifiers
                )
            )
        if path == "src/subdistricts.json":
            added, removed, changed_lists = change.postal_codes_delta
            lines.append(
                f"- postalCodes entries: +{added} / -{removed} across {changed_lists} changed lists"
            )
        if path == "src/regions.json":
            added, removed, changed_lists = change.region_province_codes_delta
            lines.append(
                f"- provinceCodes entries: +{added} / -{removed} across {changed_lists} changed lists"
            )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-sha", required=True)
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    args = parser.parse_args()
    print(render_summary(compare_git_revisions(args.repo, args.base_sha, args.head_sha)), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
