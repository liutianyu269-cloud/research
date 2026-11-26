"""Check public output properties and forward the original artifact."""

import csv
import json
import math
from pathlib import Path
import shutil
import sys


OUTPUTS = {
    "Eparse_gtb01": "eparse_report.txt", "Eparse_gtb02": "eparse_cells.jsonl",
    "MoviePy_gen01": "resized_output.mp4", "NeuroKit_gtb01": "eda_scr_metrics.csv",
    "NeuroKit_gtb02": "ecg_peaks.csv", "NeuroKit_gtb03": "eog_metrics.csv",
    "Pillow_gen01": "color_mask.png", "PyPDF2_gtb03": "pdf_metadata.json",
    "ScikitImage_gen05": "labeled_components.png", "ScikitImage_gen06": "mask.png",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate(task, artifact):
    require(artifact.is_file() and artifact.stat().st_size, f"Missing or empty {artifact.name}")
    if task == "Eparse_gtb01":
        report = artifact.read_text(encoding="utf-8")
        require(report.startswith("File name: ") and "Sheet name: " in report, "Missing workbook or worksheet heading")
        return {"worksheetHeadings": report.count("\nSheet name: ")}
    if task == "Eparse_gtb02":
        fields = {"row", "column", "value", "type", "c_header", "r_header", "excel_RC", "sheet", "f_name"}
        rows = [json.loads(line) for line in artifact.read_text(encoding="utf-8").splitlines()]
        require(rows and all(isinstance(row, dict) and fields <= row.keys() for row in rows), "Malformed cell records")
        require(len({(row["sheet"], row["excel_RC"]) for row in rows}) == len(rows), "Duplicate cell addresses")
        return {"cellRecords": len(rows)}
    if task == "PyPDF2_gtb03":
        fields = json.loads(artifact.read_text(encoding="utf-8"))
        require(isinstance(fields, dict) and fields and all(isinstance(value, str) for value in fields.values()),
                "Expected a metadata object with source text values")
        return {"fields": sorted(fields)}
    if task.startswith("NeuroKit_"):
        with artifact.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        require(len(rows) == 1, "Expected one CSV row")
        row = rows[0]
        if task == "NeuroKit_gtb01":
            count = int(row["SCR_Peaks_N"])
            deviation = float(row["EDA_Tonic_SD"])
            amplitude = row["SCR_Peaks_Amplitude_Mean"]
            require(count >= 0 and math.isfinite(deviation) and deviation >= 0, "Invalid EDA summary")
            require((not amplitude and count == 0) or (amplitude and math.isfinite(float(amplitude))), "Invalid amplitude")
            return {"peaks": count, "tonicStandardDeviation": deviation}
        if task == "NeuroKit_gtb02":
            peaks = [json.loads(row[field]) for field in ("ECG_R_Peaks", "ECG_P_Peaks")]
            for series in peaks:
                require(isinstance(series, list) and all(type(point) is int and point >= 0 for point in series)
                        and series == sorted(set(series)), "Peak positions must be ordered and unique")
            return {"rPeaks": len(peaks[0]), "pPeaks": len(peaks[1])}
        rate, times, count = [json.loads(row[field]) for field in (
            "Mean_Respiratory_Rate_BPM", "Peak_Times_Seconds", "Number_of_Peaks")]
        require(isinstance(rate, list) and isinstance(times, list) and count == [len(times)], "Inconsistent respiration lists")
        return {"respirationPeaks": len(times)}
    if task == "MoviePy_gen01":
        from moviepy import VideoFileClip
        with VideoFileClip(str(artifact)) as clip:
            require(tuple(clip.size) == (640, 480) and clip.duration > 0, "Invalid MP4 dimensions or duration")
            frame = clip.get_frame(clip.duration / 2)
            require(float(frame[:54].mean()) < 8 and float(frame[-54:].mean()) < 8, "Missing black bars")
            return {"size": clip.size, "duration": clip.duration, "blackBars": True}

    import numpy as np
    from PIL import Image

    with Image.open(artifact) as image:
        require(image.format == "PNG", "Expected PNG")
        pixels = np.asarray(image)
        if task == "ScikitImage_gen05":
            colors = np.unique(pixels.reshape(-1, 3), axis=0) if image.mode == "RGB" else []
            require(len(colors) > 1 and not colors[0].any(), "Expected RGB with black background and foreground color")
            return {"size": image.size, "foregroundColors": len(colors) - 1}
        size = (200, 200) if task == "ScikitImage_gen06" else (1200, 837)
        require(image.mode == "L" and image.size == size and set(np.unique(pixels)) == {0, 255}, "Invalid binary mask")
        return {"size": image.size, "foregroundFraction": float((pixels == 255).mean())}


def main():
    task, input_path, output_path = sys.argv[1:]
    artifact = Path(input_path) / OUTPUTS[task]
    report = validate(task, artifact)
    destination = Path(output_path)
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(artifact, destination / artifact.name)
    (destination / "artifact-validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
