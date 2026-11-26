---
name: neurokit-signals
description: Use when a recorded signal CSV needs EDA events or summary metrics, ECG peak positions, or respiration metrics.
---

# NeuroKit2 signals

Use Python 3 with NeuroKit2, pandas and NumPy. Provide the original input
directory and a separate output directory.

```sh
python scripts/signals.py CASE_ID INPUT_DIR OUTPUT_DIR
```

The original cases have the defaults below. When adapting the operation to a
recording with a documented rate, use `--sampling-rate HZ`.

| Case | Channel and method | Artifact |
| --- | --- | --- |
| `NeuroKit_gtb01` | EDA at 250 Hz, `eda_process`, mean finite SCR amplitude at peaks, peak count, population SD of tonic level | `eda_scr_metrics.csv` |
| `NeuroKit_01` | EDA at 250 Hz, `eda_process`, aligned SCR onset, peak and height arrays | `eda_events.csv` |
| `NeuroKit_gtb02` | ECG at 150 Hz, `ecg_process(method="neurokit")`, read the R and P peak event arrays | `ecg_peaks.csv` |
| `NeuroKit_02` | Same 150 Hz ECG pipeline on `NeuroKit_02_input_01.csv` | `ecg_peaks.csv` |
| `NeuroKit_gtb03` | RSP at 100 Hz on the supplied recording, `rsp_process`, mean finite respiration rate and peak times/count | `eog_metrics.csv` |

CSV outputs have one data row. Read `ECG_R_Peaks` and `ECG_P_Peaks` from
the `info` mapping returned by `ecg_process`, where events already use
zero-based sample positions. NeuroKit can return NaN for a missing P wave;
omit those entries. Verify that the remaining positions are integer, ordered,
unique, and in range before writing the two lists. Peak agreement should be
evaluated separately with the benchmark's comparison rule.
The respiration output encodes all three metrics as lists. Use the actual
`RSP` channel in the supplied recording for respiratory measures.

[NeuroKit2 ECG processing source](https://neuropsychology.github.io/NeuroKit/_modules/neurokit2/ecg/ecg_process.html)
