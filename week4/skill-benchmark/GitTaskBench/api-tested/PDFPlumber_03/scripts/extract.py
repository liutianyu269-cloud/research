"""Extract text, tables or addresses from the PDF text layer."""

import argparse
import csv
from pathlib import Path
import re

import pdfplumber

EMAIL = re.compile(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")
OUTPUTS = {
    "PDFPlumber_01": "first_page.txt",
    "PDFPlumber_02": "tables.csv",
    "PDFPlumber_03": "emails.txt",
}


def extract_tables(pages, destination):
    tables = [table for page in pages for table in page.extract_tables()]
    if not tables:
        raise ValueError("No tables found on the requested pages")
    with destination.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        for table in tables:
            writer.writerows(table)
            # A blank CSV record preserves the boundary between stacked tables.
            writer.writerow(())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task", choices=OUTPUTS)
    parser.add_argument("input_root", type=Path)
    parser.add_argument("output_root", type=Path)
    args = parser.parse_args()
    args.output_root.mkdir(parents=True, exist_ok=True)
    destination = args.output_root / OUTPUTS[args.task]
    with pdfplumber.open(args.input_root / f"{args.task}_input.pdf") as document:
        if args.task == "PDFPlumber_01":
            text = document.pages[0].extract_text()
            if not text or not text.strip():
                raise ValueError("The first page has no extractable text")
            destination.write_text(text + "\n", encoding="utf-8")
        elif args.task == "PDFPlumber_02":
            if len(document.pages) < 2:
                raise ValueError("The extraction requires two pages")
            extract_tables(document.pages[:2], destination)
        else:
            matches = {}
            for page in document.pages:
                matches.update(dict.fromkeys(EMAIL.findall(page.extract_text() or "")))
            destination.write_text("".join(address + "\n" for address in matches), encoding="utf-8")


if __name__ == "__main__":
    main()
