---
name: export-pdf-document-info
description: "读取 PDF 的 Document Info 并导出作者、标题和创建日期。"
---

# PyPDF2_gtb03

Run this workflow in the terminal as the first processing step.

```sh
python -B /workspace/skill/scripts/run_workflow.py PyPDF2_gtb03 pdf.py /workspace/input /workspace/output
```

When the command exits with code 0 and reports `"status": "validated"`, leave the artifact at `/workspace/output/pdf_metadata.json` and finish. On failure, use the reported step to identify the input, dependency or output problem.

## Input and output

Read `PyPDF2_gtb03_input.pdf`. Write `pdf_metadata.json` containing the requested document-info fields that are present.

The workflow uses `pypdf==5.5.0` in the existing DSH image; the script also supports PyPDF2 where present.

## Procedure and checks

Open with `PdfReader`. Access `/Author`, `/Title` and `/CreationDate` in `reader.metadata`; write the actual values under keys without the leading slash. Preserve the PDF date representation and check the saved JSON against the PDF.

[Source notes](references/source-notes.md)
