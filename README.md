# Thailand Geography JSON

This project contains JSON files for Thailand's geography data, including provinces, districts, subdistricts, and geography information. The data is well-structured and adheres to best practices to ensure optimal performance, ease of maintenance, and comprehensibility.

## File Structure

The project structure is as follows:

```
thailand-geography-json/
├── src/
│ ├── districts.json
│ ├── geography.json
│ ├── provinces.json
│ ├── subdistricts.json
├── .editorconfig
├── .gitignore
├── CHANGELOG.md
├── CODE_OF_CONDUCT.md
├── CONTRIBUTING.md
├── package.json
├── LICENSE
└── README.md
```

### Key files and directories

- `src/` - Contains the JSON files with the geography data.

  - `geography.json` - Contains comprehensive information for provinces, districts, and subdistricts, including postal codes.
  - `provinces.json` - Contains information about the 77 Thai provinces, including province codes and names in both English and Thai.
  - `districts.json` - Contains information about the 928 Thai districts, including district codes, names in both English and Thai, and the province code they belong to.
  - `subdistricts.json` - Contains information about the 7436 Thai subdistricts, including subdistrict codes, names in both English and Thai, and the district and province code they belong to.

- `.gitignore` - Lists files and directories that should not be tracked by Git.

- `.editorconfig` - Helps maintain consistent coding styles across different text editors and IDEs.

- `CONTRIBUTING.md` - Provides guidelines for contributors to the project.

- `CODE_OF_CONDUCT.md` - Outlines expectations for contributors and helps maintain a welcoming and inclusive community.

- `CHANGELOG.md` - Documents significant changes in the project.

- `package.json` - Manages dependencies and scripts for the project.

- `LICENSE` - Contains the MIT License for the project.

- `README.md` - Provides an overview of the project and instructions for usage.

## JSON Keys

The following keys are used in the JSON files:

- `provinceCode` - Province code, should be a number.
- `provinceNameEn` - Province name in English.
- `provinceNameTh` - Province name in Thai.
- `districtCode` - District code, should be a number.
- `districtNameEn` - District name in English.
- `districtNameTh` - District name in Thai.
- `subdistrictCode` - Subdistrict code, should be a number.
- `subdistrictNameEn` - Subdistrict name in English.
- `subdistrictNameTh` - Subdistrict name in Thai.
- `postalCode` - Postal code, should be a number with a length of 5.

## Example Usage

### JavaScript

```javascript
import geography from "./src/geography.json";
import provinces from "./src/provinces.json";
import districts from "./src/districts.json";
import subdistricts from "./src/subdistricts.json";

// Do something with the geography data, such as display it in a table or map
```

## Copyright and License

Copyright (c) 2023-Present Joe Takara. This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contributing

For details on how to contribute to the project, please read the [CONTRIBUTING.md](CONTRIBUTING.md) file.

## Code of Conduct

For details on our code of conduct and the process for submitting pull requests, please read the [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) file.

## Changelog

For details on the changes made in each version, please refer to the [CHANGELOG.md](CHANGELOG.md) file.
