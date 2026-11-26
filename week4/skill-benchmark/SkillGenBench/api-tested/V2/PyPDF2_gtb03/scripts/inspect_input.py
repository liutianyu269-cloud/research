"""Inspect public task inputs and forward them to the selected operation."""

import csv
import json
from pathlib import Path
import shutil
import sys


def inspect(task, source):
    files = sorted(path for path in source.rglob("*") if path.is_file())
    if not files:
        raise ValueError("No input files")
    family = task.split("_", 1)[0]
    if family == "Eparse":
        from openpyxl import load_workbook

        workbooks = {}
        for path in files:
            if path.suffix.lower() != ".xlsx" or path.name.startswith("~$"):
                continue
            workbook = load_workbook(path, read_only=True)
            try:
                workbooks[path.name] = workbook.sheetnames
            finally:
                workbook.close()
        if not workbooks:
            raise ValueError("No readable Excel workbooks")
        return workbooks
    if family == "PyPDF2":
        try:
            from PyPDF2 import PdfReader
        except ModuleNotFoundError:
            from pypdf import PdfReader

        with (source / f"{task}_input.pdf").open("rb") as stream:
            reader = PdfReader(stream)
            return {"pages": len(reader.pages), "metadataFields": sorted(reader.metadata or {})}
    if family == "NeuroKit":
        required = {"NeuroKit_gtb01": "EDA", "NeuroKit_gtb02": "ECG", "NeuroKit_gtb03": "RSP"}[task]
        with (source / f"{task}_input.csv").open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.reader(stream)
            channels = next(reader, [])
            if required not in channels:
                raise ValueError(f"Missing channel {required}; found {channels}")
            return {"channels": channels, "selected": required, "samples": sum(1 for _ in reader)}
    if family == "MoviePy":
        from moviepy import VideoFileClip

        with VideoFileClip(str(source / f"{task}_input.webm")) as clip:
            return {"size": list(clip.size), "duration": clip.duration, "fps": clip.fps}

    from PIL import Image

    images = {}
    for path in files:
        if path.suffix.lower() in {".png", ".jpg", ".jpeg"}:
            with Image.open(path) as image:
                images[str(path.relative_to(source))] = {"mode": image.mode, "size": image.size}
                image.verify()
    if not images:
        raise ValueError("No readable input images")
    return images


def main():
    task, input_path, output_path = sys.argv[1:]
    source, destination = Path(input_path), Path(output_path)
    metadata = inspect(task, source)
    shutil.copytree(source, destination, dirs_exist_ok=True)
    (destination / "input-inspection.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
