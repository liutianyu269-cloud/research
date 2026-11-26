"""Register and run benchmark workflows through the course API."""

import argparse
import json
from pathlib import Path
import shutil
import subprocess
from urllib.request import Request, urlopen


HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[2]
CATALOG = HERE / "catalog.json"
OUTPUT = WORKSPACE / "outputs/skill-lab-v2/manual-workflows"
STAGES = "work/skill-lab-v2/skillgenbench/workflow-stages/"
BENCHMARK_REVISION = "5a8bd61d8191e34fa1bbbffbff7f70db1d2a027d"
COLLECTIONS = {"Eparse": "eparse", "MoviePy": "moviepy", "NeuroKit": "neurokit",
               "Pillow": "pillow", "PyPDF2": "pypdf2", "ScikitImage": "scikitimage"}

# The student chose documents → parse → export, other media → identify → process,
# then verify each artifact. The catalog retains the previous expansion cases.
TASKS = {
    "Eparse_gtb01": ("parse-workbook", "check-text-report"),
    "Eparse_gtb02": ("parse-workbook", "check-cell-jsonl"),
    "MoviePy_gen01": ("identify-video", "check-letterbox-video"),
    "NeuroKit_gtb01": ("identify-signal", "check-signal-csv"),
    "NeuroKit_gtb02": ("identify-signal", "check-signal-csv"),
    "NeuroKit_gtb03": ("identify-signal", "check-signal-csv"),
    "Pillow_gen01": ("identify-color-image", "check-png-mask"),
    "PyPDF2_gtb03": ("parse-pdf", "check-metadata-json"),
    "ScikitImage_gen05": ("identify-mask-input", "check-png-mask"),
    "ScikitImage_gen06": ("identify-mask-input", "check-png-mask"),
}

TITLES = {
    "parse-workbook": "解析工作簿结构", "check-text-report": "验收工作表报告",
    "check-cell-jsonl": "验收单元格 JSON Lines", "identify-video": "识别视频尺寸与帧率",
    "check-letterbox-video": "验收补边后的视频", "identify-signal": "识别采样信号与通道",
    "check-signal-csv": "验收信号指标 CSV", "identify-color-image": "识别原图尺寸与颜色模式",
    "check-png-mask": "验收 PNG 掩膜", "parse-pdf": "解析 PDF 文档信息",
    "check-metadata-json": "验收 PDF 元数据 JSON", "identify-mask-input": "识别待处理的掩膜图像",
}


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def prepare():
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    operations = {skill["id"]: skill for skill in catalog["skills"] if skill["id"] not in TITLES}
    cases = {case["id"]: case for case in catalog["cases"]}
    stages = {}
    workflows = {}
    for task, (inspection, validation) in TASKS.items():
        case = cases[task]
        operation = operations[case["skillId"]]
        for stage, kind, port_type, script, description in (
            (inspection, "inspect", operation["inputType"], "inspect_input.py", "打开原始输入，识别结构或采样属性，并转发同一份输入。"),
            (validation, "validate", case["outputType"], "validate_artifact.py", "重新打开上一步的产物，检查格式和关键属性，保留原产物与验收记录。"),
        ):
            record = {"id": stage, "title": TITLES[stage], "description": description,
                      "source": "课程项目的工作流构件", "inputType": port_type, "outputType": port_type,
                      "script": STAGES + script, "skillFile": STAGES + f"{kind}/SKILL.md"}
            if stages.setdefault(stage, record) != record:
                raise ValueError(f"Inconsistent port types for {stage}")
        workflows[task] = {"dataset": "skillgenbench", "caseId": task, "nodes": [
            {"id": "node-inspect", "skillId": inspection, "input": {"from": "case", "port": "fixtures"}},
            {"id": "node-process", "skillId": operation["id"],
             "input": {"from": "node", "nodeId": "node-inspect", "port": "artifact"}},
            {"id": "node-validate", "skillId": validation,
             "input": {"from": "node", "nodeId": "node-process", "port": "artifact"}},
        ]}
    catalog["skills"] = [*operations.values(), *stages.values()]
    return catalog, workflows


def request(base, path, body=None, method=None):
    payload = None if body is None else json.dumps(body).encode("utf-8")
    with urlopen(Request(base + path, data=payload, method=method,
                        headers={"Content-Type": "application/json"}), timeout=150) as response:
        return json.load(response)


def prepare_fixtures(catalog, benchmark):
    revision = subprocess.check_output(["git", "-C", str(benchmark), "rev-parse", "HEAD"], text=True).strip()
    if revision != BENCHMARK_REVISION:
        raise ValueError(f"Check out SkillGenBench at {BENCHMARK_REVISION} before copying public inputs")
    for case in catalog["cases"]:
        task = case["id"]
        collection = COLLECTIONS[task.split("_", 1)[0]]
        source = benchmark / "skill_evaluation" / "code_repo" / collection / task / "context" / "input"
        destination = HERE / "inputs" / task
        if not source.is_dir():
            raise ValueError(f"Public input is absent: {source}")
        if destination.exists():
            public = {path.relative_to(source): path.read_bytes() for path in source.rglob("*") if path.is_file()}
            copied = {path.relative_to(destination): path.read_bytes()
                      for path in destination.rglob("*") if path.is_file()}
            if public != copied:
                raise ValueError(f"Existing fixtures differ for {task}; use a clean checkout")
        else:
            shutil.copytree(source, destination)
        case["inputRoot"] = destination.relative_to(WORKSPACE).as_posix()


def load_workflows(folders):
    workflows = {}
    for folder in folders:
        for source in sorted(folder.glob("*-workflow.json")):
            workflow = json.loads(source.read_text(encoding="utf-8-sig"))
            key = f"{workflow['dataset']}-{workflow['caseId']}"
            if key in workflows:
                raise ValueError(f"Duplicate workflow {key}")
            workflows[key] = workflow
    if not workflows:
        raise ValueError("No *-workflow.json files were found in the supplied folders")
    return workflows


def dispatch_composite(base, workflow, output, task, registrations):
    config = request(base, "/workflows", workflow, "PUT")
    children = [node for node in config["nodes"] if node["type"] == "flow"]
    expected = [(node["id"], registrations[node["skillId"]]["flowId"]) for node in workflow["nodes"]]
    if [(node["id"], node["reference"]) for node in children] != expected:
        raise RuntimeError(f"Wrong child flow references for {task}")
    save(output / f"{task}-rsi-flow.json", config)
    result = request(base, "/workflows/run", {"flowId": config["id"]}, "POST")
    if result["flowId"] != config["id"]:
        raise RuntimeError(f"Unexpected flow ID in the run evidence for {task}")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "run", "run-composite"))
    parser.add_argument("--api", default="http://127.0.0.1:33480/api/skill-lab/v2")
    parser.add_argument("--benchmark", type=Path, help="Reproduce the catalog using a local SkillGenBench checkout")
    parser.add_argument("--output", type=Path, default=OUTPUT, help="Save workflow and run evidence in this directory")
    parser.add_argument("--register-catalog", action="store_true", help="Register every repository Skill in the local API catalog")
    parser.add_argument("--workflow-dir", type=Path, action="append",
                        help="Source folder containing *-workflow.json for run-composite; repeat for multiple datasets")
    args = parser.parse_args()
    if args.action == "run-composite":
        if not args.workflow_dir:
            parser.error("run-composite requires at least one --workflow-dir")
        workflows = load_workflows(args.workflow_dir)
    else:
        catalog, workflows = prepare()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    for task, workflow in workflows.items():
        save(output / f"{task}-workflow.json", workflow)
    if args.action == "prepare":
        if args.benchmark:
            prepare_fixtures(catalog, args.benchmark.resolve())
        save(CATALOG, catalog)
        print(f"Saved {len(workflows)} workflows and platform catalog entries")
        return 0

    known = request(args.api, "/catalog")
    required = {node["skillId"] for flow in workflows.values() for node in flow["nodes"]}
    if args.register_catalog:
        required.update(skill["id"] for skill in known["skills"] if skill.get("script"))
    registrations = {}
    for skill_id in sorted(required):
        if skill_id not in known["registrations"]:
            raise ValueError(f"The running platform has not loaded {skill_id} in its catalog")
        state = known["registrations"][skill_id]
        if not state["loaded"]:
            state = request(args.api, f"/registry/{skill_id}", {"action": "register"}, "PUT")
        if not state["loaded"] or not state["flowId"]:
            raise ValueError(f"Failed to register {skill_id} in rsi-flow")
        registrations[skill_id] = state
    current = request(args.api, "/catalog")["registrations"]
    if any(current.get(skill_id) != state for skill_id, state in registrations.items()):
        raise RuntimeError("rsi-flow registration state changed during verification")
    save(output / "registrations.json", registrations)
    runs = {}
    for task, workflow in workflows.items():
        path = output / f"{task}-run.json"
        if args.action == "run-composite":
            result = dispatch_composite(args.api, workflow, output, task, registrations)
        else:
            result = request(args.api, "/runs", workflow, "POST")
        save(path, result)
        runs[task] = {"id": result["id"], "status": result["status"],
                      "nodes": [node["status"] for node in result["nodes"]]}
        if result.get("flowId"):
            runs[task]["flowId"] = result["flowId"]
        print(f"{task}: {runs[task]['status']} ({', '.join(runs[task]['nodes'])})", flush=True)
    save(output / "platform-summary.json", runs)
    return int(any(run["status"] != "passed" for run in runs.values()))


if __name__ == "__main__":
    raise SystemExit(main())
