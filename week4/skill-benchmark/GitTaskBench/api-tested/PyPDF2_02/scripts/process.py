"""Extract text or split a PDF using its ordered page tree."""

import argparse
from pathlib import Path
from tempfile import TemporaryDirectory

from pypdf import PdfReader, PdfWriter


def extract_text(reader, destination):
    """Write the text layer of all pages to a UTF-8 file in document order."""
    text_parts = [page.extract_text().rstrip("\n") for page in reader.pages]
    destination.write_text("\n".join(text_parts) + "\n", encoding="utf-8", newline="\n")


def split_pages(reader, destination):
    """Write one independent PDF for each page to a new output directory."""
    if destination.exists():
        raise FileExistsError(f"Use a fresh output directory: {destination}")

    with TemporaryDirectory(dir=destination.parent) as scratch:
        staged_pages = Path(scratch) / destination.name
        staged_pages.mkdir()
        for page_number, page in enumerate(reader.pages, start=1):
            writer = PdfWriter()
            writer.add_page(page)
            writer.write(staged_pages / f"page_{page_number}.pdf")
        staged_pages.rename(destination)


OPERATIONS = {
    "PyPDF2_01": (extract_text, "document.txt"),
    "PyPDF2_02": (split_pages, "pages"),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case_id", choices=OPERATIONS)
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()

    pdf_files = [
        path for path in args.input_dir.iterdir()
        if path.is_file() and path.suffix.lower() == ".pdf"
    ]
    if len(pdf_files) != 1:
        parser.error(f"Expected one input PDF, found {len(pdf_files)} in {args.input_dir}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    operation, name = OPERATIONS[args.case_id]
    destination = args.output_dir / name
    with pdf_files[0].open("rb") as input_stream:
        operation(PdfReader(input_stream), destination)
    print(destination.resolve())


if __name__ == "__main__":
    main()
