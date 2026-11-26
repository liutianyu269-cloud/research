---
name: rsp-breath-events
description: "从原题提供的呼吸波形计算平均呼吸频率、峰时刻和峰数。"
---

# NeuroKit_gtb03

Run this workflow in the terminal as the first processing step.

```sh
python -B /workspace/skill/scripts/run_workflow.py NeuroKit_gtb03 signals.py /workspace/input /workspace/output
```

When the command exits with code 0 and reports `"status": "validated"`, leave the artifact at `/workspace/output/eog_metrics.csv` and finish. On failure, use the reported step to identify the input, dependency or output problem.

## Input and output

Read `NeuroKit_gtb03_input.csv`. Write the three requested list-valued fields in `eog_metrics.csv`.

The workflow uses `neurokit2==0.2.12`, `numpy==2.2.6`, pandas.

## Procedure and checks

The provided recording exposes `RSP` and no `EOG`. Use the respiration channel with 100 Hz from the matching public recording. Compute peak times from sample indices/rate, take the mean of finite `RSP_Rate`, and check peak count equals the number of times. Use `--sampling-rate HZ` at the processing-script level for other documented rates.

[Source notes](references/source-notes.md)
