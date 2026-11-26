"""Freeze and run the selected ten-task DeepSeek Flash / DSH comparison."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import fcntl
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from gittaskbench_dsh_adapter import JUDGE_PYTHON_ENV, TASK_FORMAT, load_tasks
from online_trial import (
    HERE, RESULTS, WORKSPACE, RequestLedger, execute_trial, matching_baseline,
    read_json, run_trial, write_json,
)

ROOT = RESULTS / "mixed-score-ten-dsh"
SELECTION = WORKSPACE / "outputs/skill-lab-v2/mixed-score-ten/selection.json"
OFFICIAL = HERE / "gittaskbench"
STAGES = HERE / "skillgenbench/workflow-stages"
SGB_BUNDLES = RESULTS / "manual-baseline-ten-v5/bundles"
QUERY_HASHES = {
    "Eparse_01": "7b5a8129378cb72b1c386decbae9312ba38bd820",
    "Eparse_02": "c48272fcea8579742ee83edd464319d235fdb7d2",
    "NeuroKit_02": "8a11e18e2f7badc28c7d0e0966e14de7d4770632",
    "Faker_01": "8b28001f746d129e10fee01e51af90106cc2c5cb",
    "Faker_02": "713e8b942236425306abbc25e82573c7050d19e8",
    "PyPDF2_01": "e4774c3d93bd31ae3e84d24f6586f8627d1ed889",
    "PyPDF2_02": "f18666ad40f4cd78da438d7fce86ee8802e0e573",
}


def git_blob(content):
    return hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest()


def freeze_package(selection, results=ROOT):
    current = results / "gittaskbench-frozen"
    if current.exists():
        return current
    catalog = read_json(OFFICIAL / "catalog.json")
    skills = {skill["id"]: skill for skill in catalog["skills"]}
    with tempfile.TemporaryDirectory(dir=results, prefix="freeze-") as temporary:
        package = Path(temporary) / current.name
        package.mkdir()
        entries = []
        for selected in selection["selection"]:
            workflow = selected["workflow"]
            if workflow["dataset"] != "gittaskbench" or selected.get("reuseTrial"):
                continue
            task_id = workflow["caseId"]
            query = OFFICIAL / "official" / task_id / "query.json"
            if not query.is_file():
                query = ROOT / "query-cache" / (task_id + ".json")
            content = query.read_bytes()
            expected = selected.get("querySha") or QUERY_HASHES[task_id]
            if git_blob(content) != expected:
                content = content.replace(b"\r\n", b"\n")
            if git_blob(content) != expected:
                raise ValueError(f"Original query hash mismatch: {task_id}")
            case_dir = package / "cases" / task_id
            case_dir.mkdir(parents=True)
            (case_dir / "query.json").write_bytes(content)
            shutil.copytree(WORKSPACE / selected["inputRoot"], case_dir / "input")
            grader = f"test_scripts/{task_id}/test_script.py"
            reference = selected["reference"]
            if reference:
                original = OFFICIAL / "judge" / reference
                target = package / "judge" / reference
                target.parent.mkdir(parents=True, exist_ok=True)
                if original.is_dir():
                    shutil.copytree(original, target)
                else:
                    shutil.copyfile(original, target)
            target = package / "judge" / grader
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(OFFICIAL / "judge" / grader, target)
            entries.append({
                "id": task_id, "query": f"cases/{task_id}/query.json",
                "input": f"cases/{task_id}/input", "output": selected["expectedOutput"],
                "directory": bool(reference and (package / "judge" / reference).is_dir()),
                "grader": "judge/" + grader, "reference": "judge/" + reference if reference else None,
            })

            bundle = package / "bundles" / task_id
            scripts = bundle / "scripts"
            scripts.mkdir(parents=True)
            operation = WORKSPACE / skills[workflow["nodes"][1]["skillId"]]["script"]
            for script in (STAGES / "run_workflow.py", STAGES / "inspect_input.py",
                           STAGES / "validate_artifact.py", operation):
                shutil.copyfile(script, scripts / script.name)
            entry_point = "/workspace/skill/scripts/run_workflow.py"
            (bundle / "SKILL.md").write_text(
                f"---\nname: {task_id.lower()}-workflow\n"
                "description: Inspect the task input, run the repository operation, and validate the submission.\n---\n\n"
                f"# {task_id} workflow\n\n"
                "Run this command in the terminal. It executes the three ordered stages.\n\n"
                f"```sh\npython -B {entry_point} {task_id} {operation.name} /workspace/input /workspace/output\n```\n\n"
                "If it reports validated, the expected submission is ready. End the task. "
                "If a stage fails, read its reported error and resolve it before submitting.\n",
                encoding="utf-8",
            )
        write_json(package / "dataset.json", {
            "schema_version": 1, "id": "gittaskbench", "task_format": TASK_FORMAT,
            "version": selection["gitTaskBenchCommit"],
        })
        write_json(package / "index.json", {"schema_version": 1, "tasks": entries})
        load_tasks(package / "index.json")
        package.rename(current)
    return current


def run_slot(task_id, slot, run, *, results=ROOT):
    result = results / task_id / slot
    result.mkdir(parents=True, exist_ok=True)
    with (result / ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        previous = list(result.glob("pilot-*/summary.json"))
        if RequestLedger(result / "request-ledger.jsonl").used:
            print(f"{task_id} {slot}: paid attempt already recorded, skipping.", flush=True)
            return
        if any(read_json(item).get("exitCode") == 0 for item in previous):
            print(f"{task_id} {slot}: completed attempt already recorded, skipping.", flush=True)
            return
        print(f"{task_id} {slot}: starting", flush=True)
        run(result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("node_bin", type=Path)
    parser.add_argument("judge_python", type=Path)
    parser.add_argument("--dataset", choices=("skillgenbench", "gittaskbench", "both"), default="both")
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--selection", type=Path, default=SELECTION)
    parser.add_argument("--results", type=Path, default=ROOT)
    parser.add_argument("--task", action="append", help="Restrict the run to selected task IDs.")
    args = parser.parse_args()
    args.results.mkdir(parents=True, exist_ok=True)
    selection = read_json(args.selection)
    historical = [item["workflow"]["caseId"] for item in selection["selection"] if item.get("historicalTask")]
    _, config, original_text, _ = matching_baseline(args.project, historical[0])
    package = freeze_package(selection, args.results) if args.dataset != "skillgenbench" else None
    if args.prepare_only:
        print(package or SGB_BUNDLES)
        return
    # Resolving a virtualenv interpreter symlink would select system Python.
    judge_python = args.judge_python.absolute()
    subprocess.run([str(judge_python), "-B", "-c", "import numpy, pandas, pypdf"], check=True)
    os.environ[JUDGE_PYTHON_ENV] = str(judge_python)

    def task(selected):
        workflow = selected["workflow"]
        task_id = workflow["caseId"]
        if workflow["dataset"] == "gittaskbench":
            for slot in ("no-skill-1", "with-skill-1", "with-skill-2"):
                bundle = None if slot == "no-skill-1" else package / "bundles" / task_id
                run_slot(task_id, slot, lambda output: execute_trial(
                    args.project, args.node_bin, task_id, bundle, output, package, config, original_text,
                    dataset_module="gittaskbench_dsh_adapter", adapter_module="gittaskbench_dsh_adapter",
                ), results=args.results)
        else:
            for slot in ("with-skill-1", "with-skill-2"):
                run_slot(task_id, slot, lambda output: run_trial(
                    args.project, args.node_bin, task_id, SGB_BUNDLES / task_id,
                    results=output, short_runtime=True,
                ), results=args.results)

    selected = [item for item in selection["selection"]
                if not item.get("reuseTrial")
                and args.dataset in ("both", item["workflow"]["dataset"])
                and (args.task is None or item["workflow"]["caseId"] in args.task)]
    if args.task is not None and {item["workflow"]["caseId"] for item in selected} != set(args.task):
        parser.error("Every requested task must have a new trial in the selected dataset")
    failed = False
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(task, item): item["workflow"]["caseId"] for item in selected}
        for future, task_id in futures.items():
            try:
                future.result()
            except Exception as error:
                print(f"{task_id}: {type(error).__name__}: {error}", file=sys.stderr, flush=True)
                failed = True
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()

