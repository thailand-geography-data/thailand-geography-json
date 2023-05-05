# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.1.0] - 2023-05-06

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
