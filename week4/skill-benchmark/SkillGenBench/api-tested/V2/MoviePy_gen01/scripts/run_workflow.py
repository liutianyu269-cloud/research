"""Run the same ordered Skill stages inside the DSH task container."""

from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory

from validate_artifact import OUTPUTS


def main():
    task, operation, input_root, output_root = sys.argv[1:]
    scripts = Path(__file__).resolve().parent
    if Path(operation).name != operation:
        raise ValueError("Expected an operation script in the current bundle")
    with TemporaryDirectory(prefix="skill-flow-") as temporary:
        inspected, produced, checked = (Path(temporary) / name for name in ("inspect", "produce", "validate"))
        for script, source, target in (
            ("inspect_input.py", input_root, inspected),
            (operation, inspected, produced),
            ("validate_artifact.py", produced, checked),
        ):
            subprocess.run([sys.executable, "-B", str(scripts / script), task, str(source), str(target)], check=True)
        destination = Path(output_root)
        destination.mkdir(parents=True, exist_ok=True)
        artifact = checked / OUTPUTS[task]
        shutil.copyfile(artifact, destination / artifact.name)
        print((checked / "artifact-validation.json").read_text(encoding="utf-8").strip())


if __name__ == "__main__":
    main()
