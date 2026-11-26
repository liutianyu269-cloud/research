---
name: pdf-inspect
description: Export PDF document information as readable JSON or extract a page range while preserving page dictionary geometry with PyPDF2.
---

# PDF metadata and page extraction

Use Python 3 with PyPDF2 3.0.1 or its successor pypdf 5.5.0. The script
uses whichever is installed. Run from this skill's directory or use the
absolute path to its script.

```sh
python scripts/pdf.py CASE_ID INPUT_DIR OUTPUT_DIR
```

| Case | Input basename | Artifact basename |
| --- | --- | --- |
| `PyPDF2_gtb03` | `PyPDF2_gtb03_input.pdf` | `pdf_metadata.json` |
| `PyPDF2_gen01` | `PyPDF2_gen01_input.pdf` | `range.pdf` |

For metadata, read the document information dictionary using `PdfReader`.
Use the PDF field names without the slash, such as `Author`, `Title`, and
`CreationDate`. Keep the source date text so its precision and offset survive
the export. The default projection uses the three named fields in the task.
Use `--metadata-fields Author Title CreationDate Producer` when the caller
also needs the producer. Omit missing fields and read the JSON back.

For page selection, pages 8–15 refer to the eighth through fifteenth
physical pages. Preserve the source MediaBox, CropBox and Rotate entries
without calling accessors that can create default geometry. Read the
artifact back and confirm eight pages in the original order.

[PyPDF2 metadata guide](https://pypdf2.readthedocs.io/en/3.0.0/user/metadata.html)

## Workflow for this task

Parse the document structure, then export, and validate the produced artifact. Run this bundled workflow directly. It checks the public inputs and reopens the output before finalizing it.

```sh
python -B /workspace/skill/scripts/run_workflow.py PyPDF2_gtb03 pdf.py /workspace/input /workspace/output
```

The required artifact is `/workspace/output/pdf_metadata.json`. Read the exported JSON back and check the author, title and dates against the source PDF metadata.
Report whether the workflow succeeded. If a step fails, use its error to diagnose the input or runtime.
