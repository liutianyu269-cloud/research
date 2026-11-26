---
name: excel-eparse
description: Turn Excel workbooks into worksheet reports or one-record-per-cell JSON Lines with Eparse.
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

Use `get_df_from_file` to locate tables by worksheet and anchor, and
`df_serialize_table` to preserve cell coordinates and row/column headers.
Keep isolated populated cells in the export even when no table encloses
them. Check coverage by worksheet and Excel address.

Emit the report in workbook/worksheet order with the requested file heading.
Write cell records as individual JSON objects separated by newlines and
retain the source worksheet and filename with each record.

[Eparse source](https://github.com/ChrisPappalardo/eparse)

## Workflow selected for this task

1. Inspect the input files under `/workspace/input`.
2. Run the selected reusable operation in the current container:

   ```sh
   python /workspace/skill/scripts/excel.py Eparse_gtb01 /workspace/input /workspace/output
   ```

3. Check `/workspace/output/eparse_report.txt`. Check the file heading and make sure each source worksheet has its own table with headers and rows. Avoid replacing the full report with a preview.
4. Give a short summary of what ran and any assumptions. Leave the artifact in place.
