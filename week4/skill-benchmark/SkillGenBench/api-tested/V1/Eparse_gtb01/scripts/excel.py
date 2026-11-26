"""Produce document artifacts from the public SkillGenBench task inputs."""

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
    rows = frame.iloc[1:].set_axis(frame.iloc[0].tolist(), axis="columns")
    if rows.empty:
        return "  ".join(map(str, rows.columns))
    return rows.to_string(index=False, max_rows=None, max_cols=None)


def excel_report(input_root):
    from pandas import ExcelFile, read_excel

    directory = input_root / "Eparse_gtb01_input"
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


def excel_cells(input_root):
    from eparse.core import df_serialize_table
    from openpyxl.utils.cell import coordinate_to_tuple, get_column_letter
    from pandas import ExcelFile, isna, read_excel

    file = input_root / "Eparse_gtb02_input.xlsx"
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


TASKS = {
    "Eparse_gtb01": (excel_report, "eparse_report.txt"),
    "Eparse_gtb02": (excel_cells, "eparse_cells.jsonl"),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_id", choices=TASKS)
    parser.add_argument("input_root", type=Path)
    parser.add_argument("output_root", type=Path)
    args = parser.parse_args()
    solve, filename = TASKS[args.task_id]
    args.output_root.mkdir(parents=True, exist_ok=True)
    artifact = args.output_root / filename
    write_artifact(artifact, solve(args.input_root))
    print(artifact)


if __name__ == "__main__":
    main()
