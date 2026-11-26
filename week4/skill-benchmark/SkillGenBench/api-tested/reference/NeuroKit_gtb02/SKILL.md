---
name: extract-ecg-peak-indices
description: "在 150 Hz 的 ECG 信号中提取 R 峰与 P 峰的位置。"
---

# NeuroKit_gtb02

Run this workflow in the terminal as the first processing step.

```sh
python -B /workspace/skill/scripts/run_workflow.py NeuroKit_gtb02 signals.py /workspace/input /workspace/output
```

When the command exits with code 0 and reports `"status": "validated"`, leave the artifact at `/workspace/output/ecg_peaks.csv` and finish. On failure, use the reported step to identify the input, dependency or output problem.

## Input and output

Read the named `ECG` column from `NeuroKit_gtb02_input.csv` at 150 Hz. Output `ecg_peaks.csv` with one record and columns `ECG_R_Peaks`, `ECG_P_Peaks`.

The workflow uses `neurokit2==0.2.12`, `numpy==2.2.6`, pandas.

## Procedure and checks

Read the two event arrays returned by `ecg_process`, remove missing detections, and serialize integer sample indices as compact JSON lists inside CSV fields. Positions must be in range, unique and strictly ordered.

[Source notes](references/source-notes.md)
