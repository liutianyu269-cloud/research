"""Run the pinned GitTaskBench tasks with DSH and score their saved artifacts."""

import asyncio
import json
import os
from pathlib import Path
import shutil
import subprocess

import yaml

from datasets.package import read_package_index, resource_path
from environment.tasks import prepare_docker_runtime
from evaluation.contracts import EvaluationError, PreparedTask, Score, Task
from online_adapter import attach_bundle, upload_bundle

TASK_FORMAT = "gittaskbench-artifact-dsh-v1"
JUDGE_PYTHON_ENV = "LTY_GTB_JUDGE_PYTHON"
PROFILES = {
    "Eparse": ("eparse==0.9.2",),
    "NeuroKit": ("neurokit2==0.2.12", "numpy==2.2.6"),
    "Faker": ("faker==37.3.0",),
    "PyPDF2": ("pypdf==5.5.0",),
    "PDFPlumber": ("pdfplumber==0.11.7",),
    "Trafilatura": ("trafilatura==2.0.0", "lxml_html_clean==0.4.6"),
}


def load_tasks(index, task_ids=None):
    package = read_package_index(index, task_format=TASK_FORMAT)
    entries = {entry["id"]: entry for entry in package.index["tasks"]}
    selected = list(entries) if task_ids is None else task_ids
    tasks = []
    for task_id in selected:
        entry = entries[task_id]
        query_path = resource_path(package.root, entry["query"])
        query = json.loads(query_path.read_text(encoding="utf-8-sig"))
        if query["task_id"] != task_id:
            raise ValueError(f"Query ID differs from package entry: {task_id}")
        output = "/workspace/output/" + entry["output"]
        input_dir = resource_path(package.root, entry["input"])
        files = [path.relative_to(input_dir).as_posix()
                 for path in sorted(input_dir.rglob("*")) if path.is_file()]
        inputs = "、".join(files) if files else "此题无需输入文件"
        kind = "目录" if entry["directory"] else "文件"
        instruction = (
            query["task_description"].strip() + "\n\n"
            f"输入位于 /workspace/input。输入清单为 {inputs}。"
            f"请实际生成提交{kind} {output}。"
            "该目录可直接写入。完成提交后结束任务。"
        )
        tasks.append(Task(
            id=task_id, instruction=instruction, agent_timeout_sec=300,
            source={"package_identity": package.identity(), "revision": package.metadata["version"],
                    "root": str(package.root), "entry": entry},
        ))
    return tasks


def prepare_task(task, destination, condition):
    entry = task.source["entry"]
    root = Path(task.source["root"])
    destination = destination.resolve() / f"gittaskbench-{task.id.lower()}"
    destination.mkdir(parents=True)
    shutil.copytree(resource_path(root, entry["input"]), destination / "input")

    config = {
        "metadata": {"benchmark": "GitTaskBench", "task_id": task.id},
        "agent": {"timeout_sec": task.agent_timeout_sec},
        "sandbox": {"workdir": "/workspace", "build_timeout_sec": 1800},
        "verifier": {"timeout_sec": 120},
    }
    (destination / "task.md").write_text(
        "---\n" + yaml.safe_dump(config, sort_keys=False) + "---\n\n" + task.instruction + "\n",
        encoding="utf-8",
    )
    environment_dir = destination / "environment"
    environment_dir.mkdir()
    packages = PROFILES[task.id.split("_", 1)[0]]
    install = ["python", "-m", "pip", "install", "--no-cache-dir", *packages]
    (environment_dir / "Dockerfile").write_text(
        'FROM python:3.10-slim\nWORKDIR /workspace\n'
        f'RUN {json.dumps(install)}\nCMD ["sleep", "infinity"]\n',
        encoding="utf-8",
    )
    prepare_docker_runtime(destination, package_mirrors=False)
    prepared = PreparedTask(task_dir=destination)
    if condition == "with-skill":
        return attach_bundle(prepared, Path(os.environ["LTY_PILOT_SKILL"]))
    if condition != "no-skill":
        raise ValueError(f"Unknown condition: {condition}")
    return prepared


async def setup_environment(context):
    environment = context.environment
    result = await environment.execute(["mkdir", "-p", "/workspace/input", "/workspace/output"])
    if not result.success:
        raise RuntimeError(f"Could not initialize task directories: {result.stderr}")
    source = context.prepared.task_dir / "input"
    if any(path.is_file() for path in source.rglob("*")):
        await environment.upload(source, "/workspace/input")
    if context.prepared.skills_dir is not None:
        await upload_bundle(context)


async def evaluate(context, agent):
    entry = context.task.source["entry"]
    root = Path(context.task.source["root"])
    artifact = context.output_dir / "artifacts" / entry["output"]
    source = "/workspace/output/" + entry["output"]
    flag = "-d" if entry["directory"] else "-f"
    probe = await context.environment.execute(["test", flag, source])
    metrics = {"submitted": probe.success, "grading_status": "verifier_error"}
    if probe.success:
        await context.environment.download(source, artifact, directory=entry["directory"])
    elif probe.exit_code != 1 or probe.timed_out:
        raise EvaluationError(f"Submission check failed: {probe.stderr}", metrics)

    return await asyncio.to_thread(
        score_artifact, entry, root, artifact, context.output_dir / "verifier",
        Path(os.environ[JUDGE_PYTHON_ENV]), submitted=probe.success,
    )


def score_artifact(entry, root, artifact, verifier, judge_python, *, submitted):
    """Score a Docker submission or replay the same saved artifact on the host."""
    verifier.mkdir(parents=True, exist_ok=True)
    metrics = {"submitted": submitted, "grading_status": "verifier_error"}
    record = verifier / "native.jsonl"
    command = [
        str(judge_python), "-B", str(resource_path(root, entry["grader"])),
        "--output", str(artifact), "--result", str(record),
    ]
    if entry["reference"]:
        command.extend(("--groundtruth", str(resource_path(root, entry["reference"]))))
    with (verifier / "grader.log").open("wb") as log:
        try:
            completed = subprocess.run(
                command, cwd=verifier, stdout=log, stderr=subprocess.STDOUT, timeout=120,
            )
        except subprocess.TimeoutExpired as error:
            raise EvaluationError("The official GitTaskBench grader exceeded 120 seconds", metrics) from error
    try:
        rows = [json.loads(line) for line in record.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
        if len(rows) != 1 or completed.returncode != 0:
            raise ValueError(f"Grader exited {completed.returncode} with {len(rows)} result rows")
        native = rows[0]
        if (not isinstance(native, dict)
                or any(type(native.get(key)) is not bool for key in ("Process", "Result"))):
            raise ValueError("Grader did not report boolean Process and Result")
    except (OSError, ValueError) as error:
        raise EvaluationError(f"Could not read the official GitTaskBench score: {error}", metrics) from error
    passed = native["Process"] and native["Result"]
    metrics["native_outcome"] = native
    if passed and not submitted:
        raise EvaluationError("Grader reported a pass without a submitted artifact", metrics)
    metrics["grading_status"] = "passed" if passed else "failed" if submitted else "missing_submission"
    return Score(float(passed), metrics)

