"""Generate benchmark CSVs through reusable Faker provider mappings."""

import argparse
import csv
from pathlib import Path
import re

from faker import Faker


PROFILES = {
    "Faker_01": (
        "users.csv",
        100,
        {"Username": "user_name", "Email": "safe_email"},
    ),
    "Faker_02": (
        "companies.csv",
        5,
        {"Company Name": "company", "Address": "address", "Phone": "phone_number"},
    ),
}


def generate_csv(destination, columns, count, *, locale="en_US", seed=None):
    """Write count CSV records using an ordered mapping of headers to provider names."""
    if not columns or count < 0:
        raise ValueError("Provide at least one column and a nonnegative row count.")

    fake = Faker(locale)
    if seed is not None:
        fake.seed_instance(seed)

    providers = [getattr(fake, provider_name) for provider_name in columns.values()]
    with destination.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(columns)
        for _ in range(count):
            writer.writerow([provider() for provider in providers])


def replace_text(source, destination, *, seed):
    """Keep line breaks and word counts while replacing the original prose."""
    fake = Faker("en_US")
    fake.seed_instance(seed)
    original = source.read_text(encoding="utf-8-sig")
    lines = []
    for line in original.splitlines():
        words = re.findall(r"\b[\w']+\b", line)
        replacement = " ".join(fake.words(nb=len(words))) if words else ""
        lines.append(replacement.capitalize() + "." if replacement else "")
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case_id", choices=(*PROFILES, "Faker_03"))
    parser.add_argument("input_dir", type=Path, help="Reserved by the course runner.")
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    if args.case_id == "Faker_03":
        destination = args.output_dir / "fake_text.txt"
        replace_text(args.input_dir / "Faker_03_input.txt", destination, seed=42)
        print(destination.resolve())
        return
    filename, count, columns = PROFILES[args.case_id]
    destination = args.output_dir / filename
    generate_csv(destination, columns, count, seed=42)
    print(destination.resolve())


if __name__ == "__main__":
    main()
