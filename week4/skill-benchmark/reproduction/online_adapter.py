"""Expose just the selected skill bundle inside the original benchmark container."""

from dataclasses import replace
import hashlib
import os
from pathlib import Path
import shutil

import yaml

SKILL_ROOT = "/workspace/skill"


def skill_files(source):
    files = []
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source)
        if path.is_symlink():
            raise ValueError(f"Skill bundle contains a symbolic link: {relative}")
        if path.is_file():
            if relative != Path("SKILL.md") and relative.parts[0] not in {"scripts", "references"}:
                raise ValueError(f"Unrecognized Skill bundle file: {relative}")
            files.append(relative)
    if Path("SKILL.md") not in files:
        raise ValueError("Skill bundle has no SKILL.md")
    if sum((source / path).stat().st_size for path in files) > 256 * 1024:
        raise ValueError("Skill bundle exceeds the online pilot size limit")
    return files


def prepare_task(task, destination, condition):
    from datasets import skillgenbench

    if condition != "with-skill":
        raise ValueError("This pilot has only the with-Skill condition")
    prepared = skillgenbench.prepare_task(task, destination, "no-skill")
    return attach_bundle(prepared, Path(os.environ["LTY_PILOT_SKILL"]))


def attach_bundle(prepared, source):
    files = skill_files(source)
    markdown = (source / "SKILL.md").read_bytes()
    delimiters = markdown.decode("utf-8").replace("\r\n", "\n").split("---\n", 2)
    if len(delimiters) != 3 or delimiters[0]:
        raise ValueError("SKILL.md needs a YAML front matter block")
    metadata = yaml.safe_load(delimiters[1])
    if not isinstance(metadata, dict) or not all(
        isinstance(metadata.get(key), str) and metadata[key] for key in ("name", "description")
    ):
        raise ValueError("SKILL.md requires both a name and a description")
    skill_dir = prepared.task_dir.parent / "pilot-skill"
    skill_dir.mkdir()
    for path in files:
        copied = skill_dir / path
        copied.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / path, copied)
    return replace(prepared, skills_dir=skill_dir, skill_catalog=[{
        "name": metadata["name"],
        "description": metadata["description"],
        "path": f"{SKILL_ROOT}/SKILL.md",
        "sha256": hashlib.sha256(markdown).hexdigest(),
    }])


async def setup_environment(context):
    from datasets import skillgenbench

    prepared = context.prepared
    vanilla = replace(prepared, skills_dir=None, skill_catalog=[])
    await skillgenbench.setup_environment(replace(context, condition="no-skill", prepared=vanilla))
    await upload_bundle(context)


async def upload_bundle(context):
    prepared = context.prepared
    for path in skill_files(prepared.skills_dir):
        destination = f"{SKILL_ROOT}/{path.as_posix()}"
        result = await context.environment.execute(["mkdir", "-p", str(Path(destination).parent)])
        if not result.success:
            raise RuntimeError(f"Could not create the directory for Skill file {path}")
        await context.environment.upload(prepared.skills_dir / path, destination)
    result = await context.environment.execute(["python", "-c",
        "import hashlib,sys; from pathlib import Path; "
        "assert hashlib.sha256(Path(sys.argv[1]).read_bytes()).hexdigest() == sys.argv[2]",
        f"{SKILL_ROOT}/SKILL.md", prepared.skill_catalog[0]["sha256"]])
    if not result.success:
        raise RuntimeError("In-container Skill hash verification failed")
