---
name: neurokit-signals
description: Summarize EDA and respiration or export sample-aligned ECG peak markers from CSV with NeuroKit2.
---

# NeuroKit2 signals

Use Python 3 with NeuroKit2, pandas and NumPy. Provide the original input
directory and a separate output directory.

```sh
python scripts/signals.py CASE_ID INPUT_DIR OUTPUT_DIR
```

| Case | Channel and method | Artifact |
| --- | --- | --- |
| `NeuroKit_gtb01` | EDA at 250 Hz, `eda_process`, mean finite SCR amplitude at peaks, peak count, population SD of tonic level | `eda_scr_metrics.csv` |
| `NeuroKit_gtb02` | ECG at 150 Hz, `ecg_process`, export the `ECG_R_Peaks` and `ECG_P_Peaks` columns | `ecg_peaks.csv` |
| `NeuroKit_gtb03` | RSP at 100 Hz on the supplied recording, `rsp_process`, mean finite respiration rate and peak times/count | `eog_metrics.csv` |

CSV outputs have one data row. In the ECG export, each cell holds the
zero-based sample positions of the detected peaks. NeuroKit2's DataFrame
columns are sample-aligned 0/1 markers; convert the positions with
`np.flatnonzero(markers == 1)`. Verify ordered indices are in bounds.
The respiration output encodes all three metrics as lists. Use the actual
`RSP` channel in the supplied recording for respiratory measures.

[NeuroKit2 ECG processing source](https://neuropsychology.github.io/NeuroKit/_modules/neurokit2/ecg/ecg_process.html)

## Workflow for this task

Identify input properties, then process, and validate the produced artifact. Run this bundled workflow directly. It checks the public inputs and reopens the output before finalizing it.

```sh
python -B /workspace/skill/scripts/run_workflow.py NeuroKit_gtb02 signals.py /workspace/input /workspace/output
```

The required artifact is `/workspace/output/ecg_peaks.csv`. Export zero-based R and P peak positions as lists. Check the sampling rate and verify the indices are ordered, unique and in bounds.
Report whether the workflow succeeded. If a step fails, use its error to diagnose the input or runtime.
