"""Read PDF document information or extract a page range with PyPDF2."""

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory

try:
    from PyPDF2 import PdfReader, PdfWriter
except ModuleNotFoundError as error:
    if error.name != "PyPDF2":
        raise
    from pypdf import PdfReader, PdfWriter


GEOMETRY_KEYS = ("/MediaBox", "/CropBox", "/Rotate")


def write_metadata(reader, destination, *, fields=("Author", "Title", "CreationDate")):
    document_info = reader.metadata or {}
    payload = {field: str(document_info["/" + field]) for field in fields
               if document_info.get("/" + field) is not None}
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def direct_page_keys(node):
    """Walk the raw page tree before PdfReader flattens inherited fields."""
    if node.get("/Type") == "/Page":
        yield frozenset(key for key in GEOMETRY_KEYS if key in node)
        return
    for child in node["/Kids"]:
        yield from direct_page_keys(child.get_object())


def write_page_range(reader, destination):
    first_page, last_page = 8, 15
    leaf_keys = list(direct_page_keys(reader.trailer["/Root"]["/Pages"]))
    if len(leaf_keys) < last_page:
        raise ValueError(f"Input has {len(leaf_keys)} pages; page {last_page} is required")

    writer = PdfWriter()
    for index in range(first_page - 1, last_page):
        copied_page = writer.add_page(reader.pages[index])
        for key in GEOMETRY_KEYS:
            if key not in leaf_keys[index]:
                copied_page.pop(key, None)
    with destination.open("wb") as stream:
        writer.write(stream)


TASKS = {
    "PyPDF2_gtb03": ("pdf_metadata.json", write_metadata),
    "PyPDF2_gen01": ("range.pdf", write_page_range),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case_id", choices=TASKS)
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--metadata-fields", nargs="+", metavar="FIELD",
                        help="PDF document-info keys, case-sensitive and without the leading slash")
    arguments = parser.parse_args()
    if arguments.metadata_fields and arguments.case_id != "PyPDF2_gtb03":
        parser.error("--metadata-fields is only valid for metadata export")

    input_path = arguments.input_dir / f"{arguments.case_id}_input.pdf"
    output_name, transform = TASKS[arguments.case_id]
    arguments.output_dir.mkdir(parents=True, exist_ok=True)
    with input_path.open("rb") as source, TemporaryDirectory(dir=arguments.output_dir) as temporary:
        reader = PdfReader(source)
        if reader.is_encrypted:
            raise ValueError("Decrypt the PDF before processing it")
        staged_artifact = Path(temporary) / output_name
        if arguments.metadata_fields:
            transform(reader, staged_artifact, fields=arguments.metadata_fields)
        else:
            transform(reader, staged_artifact)
        staged_artifact.replace(arguments.output_dir / output_name)


if __name__ == "__main__":
    main()
