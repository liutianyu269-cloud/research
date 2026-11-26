---
name: inspect-benchmark-input
description: Use when a workflow must identify workbook sheets, PDF document info, signal channels or media before processing.
---

# Inspect original inputs

Open the supplied files with their format library. Record worksheet names,
PDF document-info fields, signal channels, image characteristics or video
geometry. Stop when the requested input is absent or cannot be opened.
Forward the original files along with `input-inspection.json` so the next
node can process the same bytes. The wrapper takes a case ID, an input
directory and an output directory.
