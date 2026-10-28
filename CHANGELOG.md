# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Added `src/regions.json`, the official six-region geographic division of the 77 provinces (North, Central, Northeast, East, West, South) with Thai/English region names and member `provinceCode` values, following the Royal Institute classification "การแบ่งภูมิภาคทางภูมิศาสตร์" per the National Geographical Committee 1977. Each province belongs to exactly one region.
- `scripts/validate_data.py` now validates `src/regions.json`: exactly six regions, `regionCode` 1–6 and unique, non-empty names, non-empty `provinceCodes`, referential integrity against `provinces.json`, no province in two regions, and full coverage of the 77 provinces.
- Updated `README.md` to document `regions.json` and its keys.

## [1.2.1] - 2026-10-28

### Added

- `AGENTS.md` describing data-editing integrity, the validation gate, and repository conventions for coding agents.

## [1.2.0] - 2026-10-07

### Added

- `postalCodes` key on every `subdistricts.json` and `geography.json` record, listing all postal codes of the subdistrict so it can be rendered directly as a select dropdown (primary code first), based on the official Thailand Post poster "รหัสไปรษณีย์ทั่วประเทศ จำแนกตามท้องที่" (status May 2018). Each entry carries:
  - `postalCode` - postal code used in a specific part of the subdistrict
  - `isPrimary` - `true` for the primary (majority-area) code
  - `detailTh` / `detailEn` - Thai/English description of the area (whole subdistrict, Moo (village) numbers, village names, or specific house/soi ranges)
- 86 subdistricts are served by more than one postal code and list all of their codes; the remaining 7,350 carry a single-element list.
- Added `src/multi-postal-codes.json`, an audit list of the 86 multi-postal-code subdistricts including the original poster lines (`sourceLines`) each entry was derived from. The source document is the Thailand Post poster (status May 2018): https://file.thailandpost.com/upload/content/_5e856abf6c77a.pdf.
- Updated `README.md` to document the new key.

### Changed

- `postalCode` now documents the primary (majority) postal code of a subdistrict. Existing consumers keep working, but the `postalCode` of 83 subdistricts that have a single code is also corrected; see Fixed.

### Fixed

- Postal codes of six districts that the Thailand Post poster assigns their own code: Lue Amnat 37120, Phu Phan 47310, Wang Chao 63180, Lam Thap 81190, Vibhavadi 84370, Pa Phayom 93210.
- Postal codes of three districts whose post office opened after the poster: Fao Rai 43230, Na Khu 46250, Wiang Chiang Rung 57350.
- 13 subdistricts still on codes the poster no longer assigns (24180 and 30310 are retired; Khok Sung, Lam Sonthi and Chiang Khong follow their district code).
- `districts.json` `postalCode` of nine districts that carried an exception code instead of the district's own code (Thanyaburi, Lam Luk Ka, Nong Wua So, Mueang Chiang Mai, Mae Fa Luang, Thung Saliam, Sam Roi Yot, Chulabhorn, Kanchanadit).
- `postalCode` of 101 subdistricts corrected to the code that covers most of the subdistrict (e.g. Ao Nang 81000 → 81180, Koh Tao 84280 → 84360, Nong Thale 81000 → 81180).
- `postalCodes`: 11 subdistricts wrongly listed with a second code are single-code again, 20 subdistricts now have the majority code as primary, two gained the missing district code for unlisted Moo, and garbled `detailEn` texts were rewritten.
- English names of 2 provinces, 25 districts and 98 subdistricts (including 19 in Bueng Kan province that carried the name of another subdistrict), aligned with the Department of Provincial Administration registry of 1 September 2023; trailing spaces removed from 4 names.

## [1.1.3] - 2023-05-28

### Added

- Fix Bug: Mismatched letter case and unicode issue in nameen and nameth
- Add PULL_REQUEST_TEMPLATE.md

## [1.1.2] - 2023-05-06

### Added

- Added `id` key with an integer value to each object in the following files:
  1. `src/provinces.json`
  2. `src/districts.json`
  3. `src/subdistricts.json`
  4. `src/geography.json`

### Changed

- Updated `README.md` to reflect the addition of the `id` key in the JSON files.

## [1.0.1] - 2023-05-05

### Added

- Updated README.md with new sections for Installation and Usage.

## [1.0.0] - 2023-05-03

### Added

- Initial project setup with JSON files for provinces, districts, subdistricts, and geography information.
- `src/geography.json` containing all the information from provinces, districts, and subdistricts, including postal codes.
- `src/provinces.json` containing information about Thai provinces, including province codes and names in both English and Thai.
- `src/districts.json` containing information about Thai districts, including district codes, names in both English and Thai, and the province code they belong to.
- `src/subdistricts.json` containing information about Thai subdistricts, including subdistrict codes, names in both English and Thai, and the district and province code they belong to.
- `.gitignore` file to exclude specific files and folders from being tracked by Git.
- `.editorconfig` file to maintain consistent coding styles across different text editors and IDEs.
- `CONTRIBUTING.md` file with guidelines for contributors to the project.
- `CODE_OF_CONDUCT.md` file with expectations for contributors and a welcoming, inclusive community.
- `README.md` file with an overview of the project and instructions for usage.
- `LICENSE` file containing the MIT License for the project.
