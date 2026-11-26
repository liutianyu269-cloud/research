"""Produce workbook reports and cell records from the benchmark inputs."""

import argparse
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile


def write_artifact(path, chunks):
    with NamedTemporaryFile(
        mode="w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
    ) as output:
        staged = Path(output.name)
        try:
            output.writelines(chunks)
            output.close()
            os.replace(staged, path)
        finally:
            output.close()
            staged.unlink(missing_ok=True)


def eparse_tables(workbook):
    from eparse.core import get_df_from_file

    by_sheet = {name: [] for name in workbook.sheet_names}
    for frame, anchor, _, sheet in get_df_from_file(workbook, exclude_nested=True):
        by_sheet[sheet].append((anchor, frame))
    return by_sheet


def table_text(frame):
    if frame.empty:
        return "(empty worksheet)"
    from openpyxl.utils.cell import get_column_letter

    first_row = frame.iloc[0].tolist()
    text_headers = all(isinstance(value, str) and value.strip() for value in first_row)
    if text_headers and len({value.strip() for value in first_row}) == len(first_row):
        rows = frame.iloc[1:].set_axis(first_row, axis="columns")
    else:
        headers = [get_column_letter(column + 1) for column in frame.columns]
        rows = frame.set_axis(headers, axis="columns")
    if rows.empty:
        return "  ".join(map(str, rows.columns))
    # Eparse retains zero-based workbook row numbers in the DataFrame index.
    # Include the one-based Excel row number as its own column so a leading
    # numeric cell cannot be mistaken for the row index in the text report.
    numbered = rows.rename(index=lambda row: row + 1)
    return numbered.to_string(index=True, max_rows=None, max_cols=None)


def excel_report(directory):
    from pandas import ExcelFile, read_excel

    files = sorted(
        (file for file in directory.iterdir()
         if file.is_file() and file.suffix.lower() == ".xlsx" and not file.name.startswith("~$")),
        key=lambda file: (file.name.casefold(), file.name),
    )
    if not files:
        raise ValueError(f"No Excel workbooks in {directory}")
    for file in files:
        yield f"File name: {file.name}\n"
        with ExcelFile(file) as workbook:
            for sheet, tables in eparse_tables(workbook).items():
                yield f"Sheet name: {sheet}\n"
                if not tables:
                    yield table_text(read_excel(workbook, sheet_name=sheet, header=None)) + "\n"
                for anchor, frame in tables:
                    if len(tables) > 1:
                        yield f"Table: {anchor}\n"
                    yield table_text(frame) + "\n"
        yield "\n"


def excel_cells(file):
    from eparse.core import df_serialize_table
    from openpyxl.utils.cell import coordinate_to_tuple, get_column_letter
    from pandas import ExcelFile, isna, read_excel

    with ExcelFile(file) as workbook:
        for sheet, tables in eparse_tables(workbook).items():
            cells = {}
            meta = {"sheet": sheet, "f_name": file.name}
            for _, frame in tables:
                for record in df_serialize_table(frame, **meta):
                    cells.setdefault(record["excel_RC"], record)

            # Eparse detects table rectangles. Retain isolated populated cells too.
            grid = read_excel(workbook, sheet_name=sheet, header=None)
            for row in range(grid.shape[0]):
                for column in range(grid.shape[1]):
                    address = f"{get_column_letter(column + 1)}{row + 1}"
                    if address in cells or isna(grid.iat[row, column]):
                        continue
                    one_cell = grid.iloc[row:row + 1, column:column + 1]
                    record, = df_serialize_table(one_cell, **meta)
                    record.update(row=row, column=column, c_header=None, r_header=None)
                    cells[address] = record

            for address in sorted(cells, key=coordinate_to_tuple):
                yield json.dumps(cells[address], ensure_ascii=False, allow_nan=False) + "\n"


def excel_json(file):
    worksheets = {}
    for record in excel_cells(file):
        cell = json.loads(record)
        worksheets.setdefault(cell["sheet"], []).append(cell)
    document = [{"sheet": name, "data": cells} for name, cells in worksheets.items()]
    yield json.dumps(document, ensure_ascii=False, allow_nan=False, indent=2) + "\n"


TASKS = {
    "Eparse_gtb01": (excel_report, "Eparse_gtb01_input", "eparse_report.txt"),
    "Eparse_gtb02": (excel_cells, "Eparse_gtb02_input.xlsx", "eparse_cells.jsonl"),
    "Eparse_01": (excel_report, "Eparse_01_input", "eparse_report.txt"),
    "Eparse_02": (excel_cells, "Eparse_02_input.xlsx", "eparse_cells.jsonl"),
    "Eparse_03": (excel_json, "Eparse_03_input.xlsx", "workbook.json"),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_id", choices=TASKS)
    parser.add_argument("input_root", type=Path)
    parser.add_argument("output_root", type=Path)
    args = parser.parse_args()
    solve, input_name, filename = TASKS[args.task_id]
    args.output_root.mkdir(parents=True, exist_ok=True)
    artifact = args.output_root / filename
    write_artifact(artifact, solve(args.input_root / input_name))
    print(artifact)


if __name__ == "__main__":
    main()
