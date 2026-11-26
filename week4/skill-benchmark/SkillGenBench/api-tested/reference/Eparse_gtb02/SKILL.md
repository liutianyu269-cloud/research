---
name: eparse-cells-jsonl
description: "把 Excel 工作簿中有内容的单元格导出为逐行 JSON。"
---

# Eparse_gtb02

Run this workflow in the terminal as the first processing step.

```sh
python -B /workspace/skill/scripts/run_workflow.py Eparse_gtb02 excel.py /workspace/input /workspace/output
```

When the command exits with code 0 and reports `"status": "validated"`, leave the artifact at `/workspace/output/eparse_cells.jsonl` and finish. On failure, use the reported step to identify the input, dependency or output problem.

## Input and output

Read `Eparse_gtb02_input.xlsx`. Write `eparse_cells.jsonl` as one cell object per line. Keep `row`, `column`, `value`, `type`, `c_header`, `r_header`, `excel_RC`, `sheet`, and `f_name`.

The workflow uses `eparse==0.9.2` and its pandas/openpyxl dependencies.

## Procedure and checks

Serialize Eparse table cells with their sheet and filename. Identify cells by sheet and Excel coordinate. Recover isolated populated cells from the source grid and validate the values by reading the workbook back.

[Source notes](references/source-notes.md)
