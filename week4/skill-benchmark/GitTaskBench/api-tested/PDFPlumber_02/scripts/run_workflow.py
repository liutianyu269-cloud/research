"""Run the same ordered Skill stages inside the DSH task container."""

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory

from validate_artifact import OUTPUTS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task", choices=OUTPUTS)
    parser.add_argument("operation")
    parser.add_argument("input_root", type=Path)
    parser.add_argument("output_root", type=Path)
    args = parser.parse_args()
    scripts = Path(__file__).resolve().parent
    if Path(args.operation).name != args.operation:
        parser.error("operation must be a script name in the current bundle")
    with TemporaryDirectory(prefix="skill-flow-") as temporary:
        inspected, produced, checked = (Path(temporary) / name for name in ("inspect", "produce", "validate"))
        steps = (
            ("inspect_input.py", args.input_root, inspected, []),
            (args.operation, inspected, produced, []),
            ("validate_artifact.py", produced, checked, ["--source", str(inspected)]),
        )
        for script, source, target, options in steps:
            command = [sys.executable, "-B", str(scripts / script), args.task, str(source), str(target), *options]
            step = subprocess.run(command, capture_output=True, text=True, errors="replace")
            if step.returncode:
                details = (step.stderr or step.stdout).strip()
                raise SystemExit(f"Step {script} failed (exit {step.returncode}): {details[-1600:]}")
        args.output_root.mkdir(parents=True, exist_ok=True)
        artifact = checked / OUTPUTS[args.task]
        destination = args.output_root / artifact.name
        if artifact.is_dir():
            shutil.copytree(artifact, destination)
        else:
            shutil.copyfile(artifact, destination)
        checks = json.loads((checked / "artifact-validation.json").read_text(encoding="utf-8"))
        print(json.dumps({"status": "validated", "artifact": str(destination), "checks": checks},
                         ensure_ascii=False))


if __name__ == "__main__":
    main()
