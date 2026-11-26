---
name: validate-benchmark-artifact
description: Use when an exported report, metadata JSON, signal CSV or media file must be checked before delivery.
---

# Validate the produced artifact

Reopen the previous node's artifact with the corresponding parser. Check
the format, required fields or media properties before forwarding the
file. Emit `artifact-validation.json` with the checks that ran. This is
an artifact contract check. Official benchmark scoring is run separately.

When the input directory is available, pass `--source INPUT_DIR` for the
Excel JSON Lines, PDF metadata, ECG peaks, and Otsu masks. This checks workbook
coverage and cell values, source metadata values, peak indices within the sample
range, and whether every mask pixel follows Otsu's threshold.
