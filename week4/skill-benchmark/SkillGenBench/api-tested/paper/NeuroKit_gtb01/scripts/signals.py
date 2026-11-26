"""Run the NeuroKit2 skills on the published benchmark inputs."""

import argparse
import csv
import json
from pathlib import Path

import neurokit2 as nk
import numpy as np
import pandas as pd


def read_signal(input_path, channel):
    samples = pd.read_csv(input_path, usecols=[channel])[channel].to_numpy(dtype=float)
    if not samples.size or not np.isfinite(samples).all():
        raise ValueError(f"{channel} must contain finite samples without gaps")
    return samples


def summarize_eda(input_path):
    # The matching public GitTaskBench NeuroKit_01 query specifies 250 Hz.
    sampling_rate = 250
    signals, _ = nk.eda_process(read_signal(input_path, "EDA"), sampling_rate=sampling_rate)
    peaks = signals["SCR_Peaks"].to_numpy() == 1
    amplitudes = signals.loc[peaks, "SCR_Amplitude"].to_numpy()
    amplitudes = amplitudes[np.isfinite(amplitudes)]
    return {
        "SCR_Peaks_Amplitude_Mean": float(amplitudes.mean()) if amplitudes.size else None,
        "SCR_Peaks_N": int(peaks.sum()),
        "EDA_Tonic_SD": float(np.nanstd(signals["EDA_Tonic"].to_numpy(), ddof=0)),
    }


def extract_ecg_peaks(input_path):
    samples = read_signal(input_path, "ECG")
    _, events = nk.ecg_process(samples, sampling_rate=150, method="neurokit")
    peaks = {}
    for field in ("ECG_R_Peaks", "ECG_P_Peaks"):
        positions = np.asarray(events[field], dtype=float)
        # NeuroKit represents an undetected P wave with NaN.
        positions = positions[~np.isnan(positions)]
        if (not np.isfinite(positions).all() or (positions % 1 != 0).any()
                or (positions < 0).any() or (positions >= samples.size).any()
                or (np.diff(positions) <= 0).any()):
            raise ValueError(f"{field} contains invalid or unordered sample positions")
        peaks[field] = positions.astype(int).tolist()
    return peaks


def extract_scr_events(input_path):
    _, events = nk.eda_process(read_signal(input_path, "EDA"), sampling_rate=250)
    fields = ("SCR_Onsets", "SCR_Peaks", "SCR_Height")
    values = np.column_stack([events[field] for field in fields])
    values = values[np.isfinite(values).all(axis=1)]
    return {
        "SCR_Onsets": values[:, 0].astype(int).tolist(),
        "SCR_Peaks": values[:, 1].astype(int).tolist(),
        "SCR_Height": values[:, 2].tolist(),
    }


def extract_respiratory_metrics(input_path):
    # The input begins with the same 2,175 samples as the public NeuroKit
    # example bio_resting_8min_100hz.csv bundled by GitTaskBench. It contains
    # RSP, ECG, EDA and PhotoSensor; the breathing waveform is RSP.
    sampling_rate = 100
    print("Respiratory waveform: RSP; 100 Hz from the matching NeuroKit example recording")
    signals, info = nk.rsp_process(read_signal(input_path, "RSP"), sampling_rate=sampling_rate)
    peak_times = (np.asarray(info["RSP_Peaks"], dtype=float) / sampling_rate).tolist()
    rates = signals["RSP_Rate"].to_numpy()
    rates = rates[np.isfinite(rates)]
    return {
        "Mean_Respiratory_Rate_BPM": [float(rates.mean())] if rates.size else [],
        "Peak_Times_Seconds": peak_times,
        "Number_of_Peaks": [len(peak_times)],
    }


TASKS = {
    "NeuroKit_gtb01": ("eda_scr_metrics.csv", summarize_eda),
    "NeuroKit_gtb02": ("ecg_peaks.csv", extract_ecg_peaks),
    "NeuroKit_gtb03": ("eog_metrics.csv", extract_respiratory_metrics),
    "NeuroKit_02": ("ecg_peaks.csv", extract_ecg_peaks),
    "NeuroKit_01": ("eda_events.csv", extract_scr_events),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_id", choices=TASKS)
    parser.add_argument("input_root", type=Path)
    parser.add_argument("output_root", type=Path)
    args = parser.parse_args()

    args.output_root.mkdir(parents=True, exist_ok=True)
    output_name, extract = TASKS[args.task_id]
    input_name = {
        "NeuroKit_01": "NeuroKit_inout_01.csv",
        "NeuroKit_02": "NeuroKit_02_input_01.csv",
    }.get(args.task_id, f"{args.task_id}_input.csv")
    input_path = args.input_root / input_name
    metrics = extract(input_path)
    row = [json.dumps(value, allow_nan=False) if isinstance(value, list) else value for value in metrics.values()]
    with (args.output_root / output_name).open("w", encoding="utf-8", newline="") as output:
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(metrics.keys())
        writer.writerow(row)


if __name__ == "__main__":
    main()
