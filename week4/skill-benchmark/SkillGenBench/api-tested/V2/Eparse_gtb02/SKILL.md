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

## Workflow for this task

Parse the document structure, then export, and validate the produced artifact. Run this bundled workflow directly. It checks the public inputs and reopens the output before finalizing it.

```sh
python -B /workspace/skill/scripts/run_workflow.py Eparse_gtb02 excel.py /workspace/input /workspace/output
```

The required artifact is `/workspace/output/eparse_cells.jsonl`. Read the result back line by line as JSON objects. Check the required fields and workbook cell coverage, including populated cells outside detected tables.
Report whether the workflow succeeded. If a step fails, use its error to diagnose the input or runtime.
