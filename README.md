<div align="center">
  <img src="https://user-images.githubusercontent.com/44985154/236343827-717d7324-91a6-4ed1-9d8c-c1db7c17357e.png" alt="Thailand Geography JSON">
</div>

<h1 align="center">Thailand Geography JSON</h1>

<p align="center">A user-friendly collection of well-structured JSON files containing geographical data of Thailand, including provinces, districts, subdistricts, and postal codes.</p>

<p align="center">
  <a href="https://github.com/thailand-geography-data/thailand-geography-json/blob/main/LICENSE">
    <img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-green.svg" />
  </a>
  <a href="https://github.com/thailand-geography-data/thailand-geography-json/blob/main/CHANGELOG.md">
    <img alt="version" src="https://img.shields.io/github/package-json/v/thailand-geography-data/thailand-geography-json" />
  </a>
  <a href="https://github.com/thailand-geography-data/thailand-geography-json/issues?q=is%3Aissue+is%3Aopen+label%3A%22help+wanted%22">
    <img alt="Help Wanted" src="https://img.shields.io/github/issues/thailand-geography-data/thailand-geography-json" />
  </a>
</p>

---

## Contents

- [Important Files Overview](#important-files-overview)
- [Installation](#installation)
- [Usage](#usage)
- [JSON Keys](#json-keys)
- [Sample Data](#sample-data)
- [How to Contribute](#how-to-contribute)
- [License](#license)
- [Changelog](#changelog)

## Important Files Overview

Discover the main JSON files with geographical data in the `src/` directory:

- `geography.json` - All-in-one data for provinces, districts, and subdistricts, including postal codes.
- `provinces.json` - The 77 Thai provinces with their codes and names in English and Thai.
- `districts.json` - The 928 Thai districts with codes, names in English and Thai, and related province codes.
- `subdistricts.json` - The 7,436 Thai subdistricts with codes, names in English and Thai, and corresponding district and province codes.

## Installation

This project doesn't require any specific installation steps, as it consists of static JSON files. To use the data in your project, simply download the JSON files or clone the repository using the following command:

```bash
git clone https://github.com/thailand-geography-data/thailand-geography-json.git
```

## Usage

You can directly import the JSON files into your project and use the data as needed. Below are some examples of how to import and use the JSON data in different programming languages:

### JavaScript

```javascript
import geography from "./src/geography.json";
import provinces from "./src/provinces.json";
import districts from "./src/districts.json";
import subdistricts from "./src/subdistricts.json";

// Utilize the geography data as needed, for example:
// - Display data in a table
// - Render data on a map
// - Perform data analysis and visualization
```

### Python

```python
import json

with open('./src/geography.json', 'r') as f:
    geography = json.load(f)

with open('./src/provinces.json', 'r') as f:
    provinces = json.load(f)

with open('./src/districts.json', 'r') as f:
    districts = json.load(f)

with open('./src/subdistricts.json', 'r') as f:
    subdistricts = json.load(f)

# Utilize the geography data as needed, for example:
# - Display data in a table
# - Render data on a map
# - Perform data analysis and visualization
```

## JSON Keys

Get to know the keys used in the JSON files:

- `provinceCode` - Province code (2-digit number).
- `provinceNameEn` - Province name in English (string).
- `provinceNameTh` - Province name in Thai (string).
- `districtCode` - District code (4-digit number).
- `districtNameEn` - District name in English (string).
- `districtNameTh` - District name in Thai (string).
- `subdistrictCode` - Subdistrict code (6-digit number).
- `subdistrictNameEn` - Subdistrict name in English (string).
- `subdistrictNameTh` - Subdistrict name in Thai (string).
- `postalCode` - Postal code (5-digit number).

## Sample Data

Check out sample data from each JSON file:

### provinces.json

```json
{
  "provinceCode": 10,
  "provinceNameEn": "Bangkok",
  "provinceNameTh": "กรุงเทพมหานคร"
}
```

### districts.json

```json
{
  "provinceCode": 10,
  "districtCode": 1001,
  "districtNameEn": "Phra Nakhon",
  "districtNameTh": "พระนคร",
  "postalCode": 10200
}
```

### subdistricts.json

```json
{
  "provinceCode": 10,
  "districtCode": 1001,
  "subdistrictCode": 100101,
  "subdistrictNameEn": "Phra Borom Maha Ratchawang",
  "subdistrictNameTh": "พระบรมมหาราชวัง",
  "postalCode": 10200
}
```

### geography.json

```json
{
  "provinceCode": 10,
  "provinceNameEn": "Bangkok",
  "provinceNameTh": "กรุงเทพมหานคร",
  "districtCode": 1001,
  "districtNameEn": "Phra Nakhon",
  "districtNameTh": "พระนคร",
  "subdistrictCode": 100101,
  "subdistrictNameEn": "Phra Borom Maha Ratchawang",
  "subdistrictNameTh": "พระบรมมหาราชวัง",
  "postalCode": 10200
}
```

## How to Contribute

To learn how to contribute to the project, please read the [CONTRIBUTING.md](CONTRIBUTING.md) file.

## License

Copyright (c) 2023-Present Joe Takara. This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Changelog

For information on the changes made in each version, please refer to the [CHANGELOG.md](CHANGELOG.md) file.
