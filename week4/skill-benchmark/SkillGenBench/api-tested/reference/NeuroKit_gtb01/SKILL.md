---
name: eda-scr-summary
description: "从 EDA 记录导出 SCR 幅度均值、SCR 次数和 tonic 标准差。"
---

# NeuroKit_gtb01

Run this workflow in the terminal as the first processing step.

```sh
python -B /workspace/skill/scripts/run_workflow.py NeuroKit_gtb01 signals.py /workspace/input /workspace/output
```

When the command exits with code 0 and reports `"status": "validated"`, leave the artifact at `/workspace/output/eda_scr_metrics.csv` and finish. On failure, use the reported step to identify the input, dependency or output problem.

## Input and output

Read the `EDA` column in `NeuroKit_gtb01_input.csv`. Write `eda_scr_metrics.csv` with mean SCR amplitude, SCR count and tonic standard deviation.

The workflow uses `neurokit2==0.2.12`, `numpy==2.2.6`, pandas.

## Procedure and checks

Use the 250 Hz example as the case default because the task supplies no rate. Count peak markers, average finite amplitudes at those peaks, and compute population standard deviation on the tonic series. For a different documented rate, the processing script accepts `--sampling-rate HZ`.

[Source notes](references/source-notes.md)
