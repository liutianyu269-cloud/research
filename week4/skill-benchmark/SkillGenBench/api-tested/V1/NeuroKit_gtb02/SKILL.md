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

CSV outputs have one data row. In the ECG export, each cell holds a JSON
list of one integer 0/1 marker per input sample. The marker columns in
the processed DataFrame are sample-aligned. NeuroKit2 also exposes event
indices through other interfaces for requests that explicitly need indices.
The respiration output encodes all three metrics as lists. Use the actual
`RSP` channel in the supplied recording for respiratory measures.

[NeuroKit2 ECG processing source](https://neuropsychology.github.io/NeuroKit/_modules/neurokit2/ecg/ecg_process.html)

## Workflow selected for this task

1. Inspect the input files under `/workspace/input`.
2. Run the selected reusable operation in the current container:

   ```sh
   python /workspace/skill/scripts/signals.py NeuroKit_gtb02 /workspace/input /workspace/output
   ```

3. Check `/workspace/output/ecg_peaks.csv`. Read the CSV back. Check the R and P lists, report whether they hold sample-aligned markers or event indices, and check the sampling rate from the task.
4. Give a short summary of what ran and any assumptions. Leave the artifact in place.
