"""Run the original SkillGenBench ten tasks with manually selected Skill bundles."""

import argparse
from decimal import Decimal
import fcntl
import hashlib
from pathlib import Path
import shutil
import sys

from online_adapter import SKILL_ROOT, skill_files
from online_trial import HERE, REQUEST_LIMIT, RESULTS, matching_baseline, read_json, run_trial, write_json


EXPERIMENT = RESULTS / "manual-baseline-ten-v5"
CATALOG = HERE / "skillgenbench" / "catalog.json"
STAGES = CATALOG.parent / "workflow-stages"
WORKSPACE = HERE.parents[1]
REPEATS = 2

# These checks are based on the public task instructions and input data.
CHECKS = {
    "Eparse_gtb01": "Check the file heading and make sure each source worksheet has its own table with headers and rows. Avoid replacing the full report with a preview.",
    "Eparse_gtb02": "Read the result back line by line as JSON objects. Check the fields, cell coverage and values against the workbook.",
    "MoviePy_gen01": "Open the encoded file; check its 640x480 frame size, original duration, centered black padding, and H.264 encoding.",
    "NeuroKit_gtb01": "Check the available EDA channel, then verify one CSV row contains the mean detected SCR amplitude, peak count, and tonic standard deviation. Note assumptions about sampling rate and standard deviation convention.",
    "NeuroKit_gtb02": "Export zero-based R and P peak positions as lists. Check the sampling rate and verify the indices are ordered, unique and in bounds.",
    "NeuroKit_gtb03": "List the real signal channels first. If EOG is absent, use the recorded RSP channel for the requested respiration metrics and report the assumption. Verify the CSV cells contain lists.",
    "Pillow_gen01": "Check the output is a same-size mode-L PNG and the pixel values are exactly 0 or 255. Check the hue degree-to-byte conversion before masking.",
    "PyPDF2_gtb03": "Read the exported JSON back and check the author, title and dates against the source PDF metadata.",
    "ScikitImage_gen05": "Use four-neighbor connectivity on the original binary mask. Preserve size and black background, with one distinct RGB color per foreground component.",
    "ScikitImage_gen06": "Read the result back and verify pixel-by-pixel agreement with strict greater-than Otsu thresholding at source precision. Report the foreground share without changing the output to fit a percentage.",
}

EVALUATOR_LIMITS = {
    "Eparse_gtb02": "The task requires JSON Lines but the native scorer reads a single JSON document.",
    "ScikitImage_gen05": "The native scorer expects a top-level mask and at least two foreground colors; the supplied mask is nested and has one four-connected region.",
    "ScikitImage_gen06": "The native scorer requires at least 5% foreground; source-precision Otsu produces about 1.17%.",
}

BASELINE_LIMITS = {
    "Eparse_gtb01": "The sole passing historical trace inspected a benchmark reference during the task.",
    "NeuroKit_gtb01": "The historical runs ended without a valid native score.",
    "NeuroKit_gtb03": "All historical runs exceeded the DSH time budget.",
    "ScikitImage_gen05": "The original grader could not find the supplied input mask.",
}


def fingerprints(directory):
    return {path.as_posix(): hashlib.sha256((directory / path).read_bytes()).hexdigest()
            for path in skill_files(directory)}


def freeze_plan(project, experiment=EXPERIMENT):
    catalog = read_json(CATALOG)
    skills = {skill["id"]: skill for skill in catalog["skills"]}
    cases = {case["id"]: case for case in catalog["cases"]}
    plan_file = experiment / "plan.json"
    if plan_file.is_file():
        plan = read_json(plan_file)
        for row in plan["tasks"]:
            if fingerprints(experiment / row["bundle"]) != row["skillFiles"]:
                raise ValueError(f"Frozen Skill bundle changed for {row['task']}")
        return plan

    if experiment != EXPERIMENT:
        raise FileNotFoundError(f"The selected experiment needs a prepared plan: {plan_file}")
    experiment.mkdir(parents=True, exist_ok=True)
    rows = []
    for task_id, check in CHECKS.items():
        _, _, _, baseline = matching_baseline(project, task_id, allow_unscored_baseline=True)
        case = cases[task_id]
        skill = skills[case["skillId"]]
        script = WORKSPACE / skill["script"]
        bundle = Path("bundles") / task_id
        directory = experiment / bundle
        (directory / "scripts").mkdir(parents=True, exist_ok=True)
        source = script.parents[1] / "SKILL.md"
        command = (f"python -B {SKILL_ROOT}/scripts/run_workflow.py {case['skillArgument']} "
                   f"{script.name} /workspace/input /workspace/output")
        shutil.copyfile(script, directory / "scripts" / script.name)
        for stage in ("inspect_input.py", "validate_artifact.py", "run_workflow.py"):
            shutil.copyfile(STAGES / stage, directory / "scripts" / stage)
        frontmatter, _, details = source.read_text(encoding="utf-8").removeprefix("---\n").partition("\n---\n")
        if not details:
            raise ValueError(f"Skill front matter is missing or incomplete: {source}")
        workflow = ("## Run this task\n\n"
                    "Use the bundled workflow as your first processing command. It inspects the original input, "
                    "runs the selected operation, and validates the output.\n\n"
                    f"```sh\n{command}\n```\n\n"
                    f"Exit code 0 and `status: validated` mean `/workspace/output/{case['expectedOutput']}` "
                    "has been written and passed the bundled checks. Leave it in place and give a short final answer. "
                    "The terminal response includes the checks. Inspect the named failing step if the command fails.\n\n"
                    f"## Task details\n\n{check}\n")
        (directory / "SKILL.md").write_text(
            f"---\n{frontmatter}\n---\n\n{workflow}\n{details.lstrip()}", encoding="utf-8", newline="\n",
        )
        hashes = fingerprints(directory)
        rows.append({"task": task_id, "title": case["title"], "skill": skill["id"], "source": skill["source"],
                     "bundle": bundle.as_posix(), "skillFiles": hashes, "command": command,
                     "output": case["expectedOutput"], "outputCheck": check,
                     "historicalNoSkillScore": baseline["no_skill_mean_native_score"],
                     "historicalNoSkillTrials": baseline["no_skill"],
                     "evaluatorLimit": EVALUATOR_LIMITS.get(task_id), "baselineLimit": BASELINE_LIMITS.get(task_id)})
    plan = {"baseline": "liutianyu-sgb-matrix-r1", "harness": "dsh", "model": "deepseek-flash",
            "gateway": "Thingo", "trialsPerTask": REPEATS, "requestLimitPerTrial": REQUEST_LIMIT,
            "tasks": rows}
    write_json(plan_file, plan)
    return plan


def task_result(results):
    runs = sorted(results.glob("pilot-*/summary.json"))
    if len(runs) > 1:
        paid_runs = [path for path in runs if read_json(path)["actualRequests"] > 0]
        if len(paid_runs) > 1:
            raise ValueError(f"More than one trial used requests in {results}")
        runs = paid_runs or runs[-1:]
    return read_json(runs[0]) if runs else None


def summarize(plan, experiment=EXPERIMENT):
    rows = []
    new_requests = 0
    new_cost = Decimal(0)
    new_cost_complete = True
    for task in plan["tasks"]:
        trials = []
        for repeat in range(1, REPEATS + 1):
            result = task_result(experiment / "trials" / task["task"] / str(repeat))
            if result is None:
                trials.append(None)
                continue
            trials.append({**result, "repeat": repeat})
            new_requests += result["actualRequests"]
            usage = result.get("agentUsage") or {}
            cost = (usage.get("accounting") or {}).get("estimated_totals", {}).get("CNY")
            if cost is not None:
                new_cost += Decimal(cost)
            elif result["actualRequests"]:
                new_cost_complete = False
        rows.append({**task, "withSkillTrials": trials})
    report = {"baseline": plan["baseline"], "model": plan["model"], "gateway": plan["gateway"],
              "harness": plan["harness"], "tasks": rows, "newGatewayRequests": new_requests,
              "recordedNewCostCNY": str(new_cost), "newCostComplete": new_cost_complete}
    write_json(experiment / "summary.json", report)
    print(f"{sum(trial is not None for row in rows for trial in row['withSkillTrials'])}/20 trial reports; "
          f"{new_requests} new gateway requests; recorded cost {new_cost} CNY")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("node_bin", type=Path)
    parser.add_argument("action", choices=["plan", "run", "summarize"])
    parser.add_argument("task", nargs="?", choices=CHECKS)
    parser.add_argument("repeat", nargs="?", type=int, choices=range(1, REPEATS + 1))
    parser.add_argument("--experiment", type=Path, default=EXPERIMENT,
                        help="Use a separately prepared Skill plan and write results there.")
    args = parser.parse_args()
    project = args.project.resolve()
    experiment = args.experiment.resolve()
    plan = freeze_plan(project, experiment)
    if args.action == "plan":
        for row in plan["tasks"]:
            print(f"{row['task']}: {row['skill']} x{REPEATS}")
        return 0
    if args.action == "summarize":
        summarize(plan, experiment)
        return 0
    if args.task is None or args.repeat is None:
        parser.error("run requires a task and a repeat number")
    row = next(row for row in plan["tasks"] if row["task"] == args.task)
    results = experiment / "trials" / args.task / str(args.repeat)
    previous = task_result(results)
    if previous and previous["actualRequests"]:
        print(f"Keeping the existing trial for {args.task}")
        return 0
    results.mkdir(parents=True, exist_ok=True)
    with (results / ".trial.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return run_trial(project, args.node_bin.resolve(), args.task, experiment / row["bundle"],
                         results=results, allow_unscored_baseline=True, short_runtime=True)


if __name__ == "__main__":
    sys.exit(main())
