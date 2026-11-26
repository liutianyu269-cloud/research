---
name: eparse-workbook-report
description: "将目录里的多个工作簿整理为一份可读的工作表报告。"
---

# Eparse_gtb01

Run this workflow in the terminal as the first processing step.

```sh
python -B /workspace/skill/scripts/run_workflow.py Eparse_gtb01 excel.py /workspace/input /workspace/output
```

When the command exits with code 0 and reports `"status": "validated"`, leave the artifact at `/workspace/output/eparse_report.txt` and finish. On failure, use the reported step to identify the input, dependency or output problem.

## Input and output

Read every XLSX under `Eparse_gtb01_input/`. Write `eparse_report.txt` with each actual workbook name, every worksheet in order, and full DataFrame-style rows.

The workflow uses `eparse==0.9.2` and its pandas/openpyxl dependencies.

## Procedure and checks

Use the Eparse workbook parser to identify tables and sheet context. Read the whole worksheet when parsing only finds a portion or multiple tables. Preserve the data and the actual worksheet names.

[Source notes](references/source-notes.md)
