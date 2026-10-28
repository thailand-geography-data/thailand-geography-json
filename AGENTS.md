# AGENTS.md

Thailand geography data, shipped as static JSON under `src/`. Data is the product: no build, no runtime, no third-party dependency.

## Editing data

The five datasets are mutually consistent, and `scripts/validate_data.py` enforces that consistency. Every data change is a multi-file edit:

- `geography.json` is a denormalized join of provinces, districts, and subdistricts. A change to any record in `provinces.json`, `districts.json`, or `subdistricts.json` must be propagated to the matching `geography.json` record.
- `multi-postal-codes.json` is an audit of every subdistrict served by more than one postal code. When a `postalCodes` list gains or loses an entry, update this file so its `subdistrictCode` set stays equal to the set of multi-postal subdistricts.

Do not invent data. Postal codes come from the Thailand Post poster "รหัสไปรษณีย์ทั่วประเทศ จำแนกตามท้องที่" (May 2018); English names come from the Department of Provincial Administration registry (1 September 2023). Cite the source in the commit, and in CHANGELOG.md for a non-obvious value.

## Verifying a data change

Run both, from the repo root, and fix every reported error:

```bash
python3 -m unittest discover -s tests -v
python3 scripts/validate_data.py
```

`validate_data.py` is the single source of truth for invariants: schema, code widths, referential integrity, postal-code rules, geography/subdistrict set equality, and the multi-postal audit. When it reports a mismatch, fix the data, not the validator.

Done when both commands exit 0. CI (`.github/workflows/validate-data.yml`) runs the same two commands plus a change summary on every pull request.

## Conventions

- Python standard library only, in `scripts/` and `tests/`. Do not add third-party dependencies. `package.json` is metadata only (`main` points at `src/geography.json`); there is no install step.
- README and CHANGELOG hardcode dataset counts (77 provinces, 928 districts, 7,436 subdistricts, 86 multi-postal). Update them when a change alters those numbers.
- Document data changes under `[Unreleased]` in CHANGELOG.md (Keep a Changelog). Releases bump `package.json` `version` and date the section.

## Schema and usage

Authoritative: README "JSON Keys" and "Sample Data", and `RECORD_SCHEMAS` in `scripts/validate_data.py`. Do not restate them here.
