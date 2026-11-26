---
name: excel-eparse
description: Use when an Excel workbook must be exported as a worksheet report or one JSON object per populated cell.
---

# Eparse workbook exports

Use Python 3 with Eparse 0.9.2, pandas and openpyxl.

```sh
python scripts/excel.py CASE_ID INPUT_DIR OUTPUT_DIR
```

| Case | Input | Artifact |
| --- | --- | --- |
| `Eparse_gtb01` | `Eparse_gtb01_input/` | `eparse_report.txt` |
| `Eparse_gtb02` | `Eparse_gtb02_input.xlsx` | `eparse_cells.jsonl` |
| `Eparse_01` | `Eparse_01_input/` | `eparse_report.txt` |
| `Eparse_02` | `Eparse_02_input.xlsx` | `eparse_cells.jsonl` |

Use `get_df_from_file` to locate tables by worksheet and anchor, and
`df_serialize_table` to preserve cell coordinates and row/column headers.
Keep isolated populated cells in the export even when no table encloses
them. Check coverage by worksheet and Excel address.

Emit the report in workbook/worksheet order with the requested file heading.
For `Eparse_gtb01`, use Excel column letters and preserve the first physical
row and literal values such as `NA`. For `Eparse_01`, use a leading row of
distinct, nonempty text as column labels when available.
Render the source's one-based Excel row numbers in the index column, separate
from the cell data. Use the index to find the original rows in the workbook.
Write cell records as individual JSON objects separated by newlines and
retain the source worksheet and filename with each record. Verify coverage
and serialized values against the workbook's populated cell coordinates.
Read JSON Lines one line
at a time. A coverage summary is enough to review a successful export.

[Eparse source](https://github.com/ChrisPappalardo/eparse)
