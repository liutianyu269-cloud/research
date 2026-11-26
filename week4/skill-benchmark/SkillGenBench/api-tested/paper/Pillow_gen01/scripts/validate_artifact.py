"""Check public output properties and forward the original artifact."""

import argparse
import csv
import json
import math
from pathlib import Path
import shutil


OUTPUTS = {
    "Eparse_gtb01": "eparse_report.txt", "Eparse_gtb02": "eparse_cells.jsonl",
    "MoviePy_gen01": "resized_output.mp4", "NeuroKit_gtb01": "eda_scr_metrics.csv",
    "NeuroKit_gtb02": "ecg_peaks.csv", "NeuroKit_gtb03": "eog_metrics.csv",
    "Pillow_gen01": "color_mask.png", "PyPDF2_gtb03": "pdf_metadata.json",
    "ScikitImage_gen05": "labeled_components.png", "ScikitImage_gen06": "mask.png",
    "Eparse_01": "eparse_report.txt", "Eparse_02": "eparse_cells.jsonl", "NeuroKit_02": "ecg_peaks.csv",
    "Eparse_03": "workbook.json", "NeuroKit_01": "eda_events.csv", "Faker_03": "fake_text.txt",
    "PDFPlumber_01": "first_page.txt", "PDFPlumber_02": "tables.csv", "PDFPlumber_03": "emails.txt",
    "Trafilatura_01": "article.txt",
    "Faker_01": "users.csv", "Faker_02": "companies.csv",
    "PyPDF2_01": "document.txt", "PyPDF2_02": "pages",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate(task, artifact, source=None):
    if task == "PyPDF2_02":
        from pypdf import PdfReader

        require(artifact.is_dir(), "Missing output page directory")
        pages = sorted(artifact.glob("*.pdf"))
        require(pages and {page.name for page in pages} == {f"page_{index}.pdf" for index in range(1, len(pages) + 1)},
                "Page filenames must be consecutive")
        for page in pages:
            with page.open("rb") as stream:
                require(len(PdfReader(stream).pages) == 1, f"{page.name} contains more or fewer than one page")
        return {"singlePagePdfs": len(pages)}

    require(artifact.is_file() and artifact.stat().st_size, f"Missing or empty {artifact.name}")
    if task in {"Eparse_gtb01", "Eparse_01"}:
        report = artifact.read_text(encoding="utf-8")
        require(report.startswith("File name: ") and "Sheet name: " in report, "Missing workbook or worksheet heading")
        headings = [line for line in report.splitlines() if line.startswith(("File name: ", "Sheet name: "))]
        if source is not None and task == "Eparse_gtb01":
            from openpyxl import load_workbook

            input_dir = source / f"{task}_input"
            expected = []
            books = sorted((path for path in input_dir.glob("*")
                            if path.is_file() and path.suffix.lower() == ".xlsx" and not path.name.startswith("~$")),
                           key=lambda path: (path.name.casefold(), path.name))
            for path in books:
                expected.append(f"File name: {path.name}")
                workbook = load_workbook(path, read_only=True)
                try:
                    expected.extend(f"Sheet name: {name}" for name in workbook.sheetnames)
                finally:
                    workbook.close()
            require(headings == expected, "The report does not cover the source workbooks and worksheets in order")
        return {"worksheetHeadings": sum(line.startswith("Sheet name: ") for line in headings)}
    if task in {"Eparse_gtb02", "Eparse_02", "Eparse_03"}:
        fields = {"row", "column", "value", "type", "c_header", "r_header", "excel_RC", "sheet", "f_name"}
        text = artifact.read_text(encoding="utf-8")
        if task == "Eparse_03":
            worksheets = json.loads(text)
            rows = [cell for worksheet in worksheets for cell in worksheet["data"]]
        else:
            rows = [json.loads(line) for line in text.splitlines()]
        require(isinstance(rows, list) and rows and all(isinstance(row, dict) and fields <= row.keys() for row in rows),
                "Malformed cell records")
        addresses = {(row["sheet"], row["excel_RC"]) for row in rows}
        require(len(addresses) == len(rows), "Duplicate cell addresses")
        checks = {"cellRecords": len(rows)}
        if source is not None:
            from eparse.core import df_normalize_data
            from openpyxl import load_workbook

            workbook_path = source / f"{task}_input.xlsx"
            require(all(row["f_name"] == workbook_path.name for row in rows), "Incorrect workbook filename in JSON Lines")
            workbook = load_workbook(workbook_path, read_only=True, data_only=True)
            try:
                populated = {(sheet.title, cell.coordinate): cell.value for sheet in workbook for row in sheet.iter_rows()
                             for cell in row if cell.value is not None}
            finally:
                workbook.close()
            missing = populated.keys() - addresses
            require(not missing, f"Missing {len(missing)} populated workbook cells")
            for row in rows:
                address = (row["sheet"], row["excel_RC"])
                if address in populated:
                    expected = df_normalize_data({"value": populated[address]})["value"]
                    require(row["value"] == expected, f"Incorrect cell value at {address[0]}!{address[1]}")
            checks["populatedSourceCells"] = len(populated)
            checks["matchesSourceCellValues"] = True
        return checks
    if task == "PyPDF2_gtb03":
        fields = json.loads(artifact.read_text(encoding="utf-8"))
        require(isinstance(fields, dict) and fields and all(isinstance(value, str) for value in fields.values()),
                "Expected a metadata object with source text values")
        checks = {"fields": sorted(fields)}
        if source is not None:
            try:
                from PyPDF2 import PdfReader
            except ModuleNotFoundError as error:
                if error.name != "PyPDF2":
                    raise
                from pypdf import PdfReader

            with (source / "PyPDF2_gtb03_input.pdf").open("rb") as stream:
                metadata = PdfReader(stream).metadata or {}
                required = {field for field in ("Author", "Title", "CreationDate") if metadata.get("/" + field) is not None}
                require(required <= fields.keys(), "Missing a named metadata field present in the PDF")
                for field, value in fields.items():
                    original = metadata.get("/" + field)
                    require(original is not None and str(original) == value,
                            f"Metadata field {field} differs from the source PDF")
            checks["matchesSourceMetadata"] = True
        return checks
    if task == "Faker_03":
        replacement = artifact.read_text(encoding="utf-8")
        lines = len(replacement.splitlines())
        require(replacement.strip(), "The replacement text is empty")
        if source is not None:
            original = (source / "Faker_03_input.txt").read_text(encoding="utf-8-sig")
            require(replacement.strip() != original.strip(), "The replacement text is unchanged")
            require(lines == len(original.splitlines()), "The line structure changed")
        return {"lines": lines}
    if task.startswith("Faker_"):
        expected = ("Username", "Email") if task == "Faker_01" else ("Company Name", "Address", "Phone")
        count = 100 if task == "Faker_01" else 5
        with artifact.open(encoding="utf-8", newline="") as stream:
            reader = csv.reader(stream)
            require(tuple(next(reader, [])) == expected, "Unexpected synthetic CSV header")
            rows = list(reader)
        require(len(rows) == count and all(len(row) == len(expected) and all(value.strip() for value in row) for row in rows),
                "Unexpected CSV row count or empty fields")
        return {"rows": count, "fields": expected}
    if task == "PyPDF2_01":
        text = artifact.read_text(encoding="utf-8")
        require(text.strip(), "Empty PDF text output")
        return {"textCharacters": len(text)}
    if task in {"PDFPlumber_01", "Trafilatura_01"}:
        text = artifact.read_text(encoding="utf-8")
        require(text.strip(), "The extracted text is empty")
        return {"textCharacters": len(text)}
    if task == "PDFPlumber_02":
        with artifact.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.reader(stream))
        require(any(any(cell.strip() for cell in row) for row in rows), "The table CSV contains no data")
        return {"tableRows": len(rows)}
    if task == "PDFPlumber_03":
        emails = artifact.read_text(encoding="utf-8").splitlines()
        require(all(line.count("@") == 1 and line.strip() == line for line in emails), "Expected one email address per line")
        return {"emails": len(emails)}
    if task.startswith("NeuroKit_"):
        with artifact.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        require(len(rows) == 1, "Expected one CSV row")
        row = rows[0]
        if task == "NeuroKit_01":
            onsets, peaks, heights = [json.loads(row[field]) for field in ("SCR_Onsets", "SCR_Peaks", "SCR_Height")]
            require(len(onsets) == len(peaks) == len(heights), "The EDA event columns have inconsistent lengths")
            require(all(0 <= onset <= peak for onset, peak in zip(onsets, peaks)), "An SCR peak precedes its onset")
            require(all(math.isfinite(height) for height in heights), "An SCR height is not finite")
            return {"scrEvents": len(peaks)}
        if task == "NeuroKit_gtb01":
            count = int(row["SCR_Peaks_N"])
            deviation = float(row["EDA_Tonic_SD"])
            amplitude = row["SCR_Peaks_Amplitude_Mean"]
            require(count >= 0 and math.isfinite(deviation) and deviation >= 0, "Invalid EDA summary")
            require((not amplitude and count == 0) or (amplitude and math.isfinite(float(amplitude))), "Invalid amplitude")
            return {"peaks": count, "tonicStandardDeviation": deviation}
        if task in {"NeuroKit_gtb02", "NeuroKit_02"}:
            peaks = [json.loads(row[field]) for field in ("ECG_R_Peaks", "ECG_P_Peaks")]
            for series in peaks:
                require(isinstance(series, list) and all(type(point) is int and point >= 0 for point in series)
                        and series == sorted(set(series)), "Peak positions must be ordered and unique")
            checks = {"rPeaks": len(peaks[0]), "pPeaks": len(peaks[1])}
            if source is not None:
                input_name = "NeuroKit_02_input_01.csv" if task == "NeuroKit_02" else "NeuroKit_gtb02_input.csv"
                with (source / input_name).open(encoding="utf-8-sig", newline="") as stream:
                    sample_count = sum(1 for _ in csv.DictReader(stream))
                require(sample_count > 0 and all(position < sample_count for series in peaks for position in series),
                        f"Peak position is outside the {sample_count} source samples")
                checks["sourceSamples"] = sample_count
            return checks
        rate, times, count = [json.loads(row[field]) for field in (
            "Mean_Respiratory_Rate_BPM", "Peak_Times_Seconds", "Number_of_Peaks")]
        require(isinstance(rate, list) and isinstance(times, list) and count == [len(times)], "Inconsistent respiration lists")
        require(len(rate) <= 1 and all(isinstance(value, (int, float)) and math.isfinite(value) and value > 0
                                      for value in rate), "Invalid mean respiratory rate")
        require(all(isinstance(value, (int, float)) and math.isfinite(value) and value >= 0 for value in times)
                and times == sorted(set(times)), "Peak times must be finite, nonnegative and strictly ordered")
        return {"respirationPeaks": len(times)}
    if task == "MoviePy_gen01":
        from moviepy import VideoFileClip
        with VideoFileClip(str(artifact)) as clip:
            require(tuple(clip.size) == (640, 480) and clip.duration > 0, "Invalid MP4 dimensions or duration")
            frame = clip.get_frame(clip.duration / 2)
            require(float(frame[:54].mean()) < 8 and float(frame[-54:].mean()) < 8, "Missing black bars")
            checks = {"size": clip.size, "duration": clip.duration, "blackBars": True}
            if source is not None:
                with VideoFileClip(str(source / f"{task}_input.webm")) as original:
                    require(original.fps > 0 and abs(clip.duration - original.duration) <= 2 / original.fps + 0.01,
                            "The resized video changed the source duration")
                checks["matchesSourceDuration"] = True
            return checks

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
        foreground = pixels == 255
        checks = {"size": image.size, "foregroundFraction": float(foreground.mean())}
        if task == "Pillow_gen01" and source is not None:
            with Image.open(source / f"{task}_input.jpg") as original:
                hue, saturation, value = np.moveaxis(np.asarray(original.convert("RGB").convert("HSV")), -1, 0)
            expected = (hue >= 15) & (hue <= 28) & (saturation >= 77) & (value >= 102)
            require(np.array_equal(foreground, expected), "Mask pixels do not match the specified HSV range")
            checks["matchesSourceHSV"] = True
        if task == "ScikitImage_gen06" and source is not None:
            from skimage.filters import threshold_otsu

            with Image.open(source / "ScikitImage_gen06_input.png") as original:
                gray = np.asarray(original)
                require(gray.ndim == 2 and original.size == image.size, "Invalid source grayscale image")
                threshold = threshold_otsu(gray)
            require(np.array_equal(foreground, gray > threshold), "Mask pixels differ from the source Otsu result")
            checks["otsuThreshold"] = float(threshold)
        return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task", choices=OUTPUTS)
    parser.add_argument("input_path", type=Path)
    parser.add_argument("output_path", type=Path)
    parser.add_argument("--source", type=Path)
    args = parser.parse_args()
    artifact = args.input_path / OUTPUTS[args.task]
    report = validate(args.task, artifact, args.source)
    destination = args.output_path
    destination.mkdir(parents=True, exist_ok=True)
    if artifact.is_dir():
        shutil.copytree(artifact, destination / artifact.name)
    else:
        shutil.copyfile(artifact, destination / artifact.name)
    (destination / "artifact-validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
