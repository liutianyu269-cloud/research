"""不启动 harness 的环境预检和历史产物评分。"""

import asyncio
import hashlib
import json
from pathlib import Path
from tempfile import mkdtemp
from time import monotonic

from datasets.package import resource_path
from utils.json_io import write_json

from .config import load_function
from .contracts import PreparedTask, Task, TrialContext, validate_score
from .experiment import iter_trials, load_run


def _read_record(path: Path) -> tuple[dict, str]:
    contents = path.read_bytes()
    record = json.loads(contents)
    if not isinstance(record, dict) or record.get("schema_version") != 1:
        raise ValueError(f"不支持的实验记录格式：{path}")
    return record, hashlib.sha256(contents).hexdigest()


def _load_replay(config: dict, trial_dir: Path) -> tuple[Task, dict, Path, dict]:
    if trial_dir.parent.name != "trials":
        raise ValueError("请提供实验目录下 trials/<trial_id> 的路径")
    trial_dir = resource_path(trial_dir.parent.parent, f"trials/{trial_dir.name}")
    manifest, manifest_hash = _read_record(resource_path(trial_dir.parent.parent, "manifest.json"))
    original, result_hash = _read_record(resource_path(trial_dir, "result.json"))
    artifacts = resource_path(trial_dir, "artifacts")
    if not artifacts.is_dir():
        raise ValueError(f"试验产物目录不存在：{artifacts}")

    if original.get("status") not in {"completed", "error", "cancelled"}:
        raise ValueError("只支持已结束且保留产物的试验")
    task_id, condition, repeat = original["task_id"], original["condition"], original["repeat"]
    if (type(repeat) is not int or repeat < 1
            or original["trial_id"] != f"{task_id}__{condition}__{repeat:03d}"
            or original["trial_id"] != trial_dir.name):
        raise ValueError("试验记录 ID、条件或轮次与目录不匹配")
    dataset = config["dataset"]
    saved_config = manifest["config"]
    for key in ("package_identity", "loader", "prepare", "setup"):
        if saved_config["dataset"].get(key) != dataset.get(key):
            raise ValueError(f"当前数据集的 {key} 与原实验不一致，请选择原资源包及配置")
    if saved_config["environment"] != config["environment"]:
        raise ValueError("当前环境配置与原实验不一致，请选择原环境配置")
    evaluator = config["evaluator"]["function"]
    if original["evaluator"] != evaluator or manifest["components"]["evaluator"] != evaluator:
        raise ValueError("当前原生评分器与原实验的评分器入口不一致")

    task, = load_function(dataset["loader"])(Path(dataset["index"]), [task_id])
    saved_task = next((item for item in manifest["tasks"] if item["id"] == task_id), None)
    if (saved_task is None or task.id != task_id or task.instruction != saved_task["instruction"]
            or any(task.source[key] != saved_task["source"].get(key)
                   for key in ("bundle_sha256", "docs_sha256"))):
        raise ValueError(f"当前任务资料与原始清单不一致：{task_id}")
    source = {
        "trial_dir": str(trial_dir), "trial_id": original["trial_id"],
        "experiment_id": manifest["experiment_id"],
        "manifest_sha256": manifest_hash, "result_sha256": result_hash,
        "status": original["status"], "reward": original.get("reward"),
        "passed": original.get("passed"), "pass_threshold": saved_config["pass_threshold"],
    }
    return task, original, artifacts, source


async def run_artifact_checks(config: dict, *, source_trial: Path | None = None) -> tuple[Path, bool]:
    """按当前任务条件预检，或按旧试验条件在新环境中回放文件。"""
    hook = config["evaluator"].get("artifact_replay")
    if hook is None:
        raise ValueError("当前基准未配置 evaluator.artifact_replay，无法执行预检或产物重评")
    dataset = config["dataset"]
    artifacts, source = None, None
    if source_trial is None:
        tasks, _, _ = load_run(config)
        entries = iter_trials(tasks, config["conditions"], 1)
        mode, threshold = "preflight", config["pass_threshold"]
    else:
        task, original, artifacts, source = _load_replay(config, source_trial)
        entries = [(task, original["condition"], original["repeat"], original["trial_id"])]
        mode, threshold = "rescore", source["pass_threshold"]

    prepare = load_function(dataset["prepare"])
    setup = load_function(dataset["setup"]) if dataset.get("setup") else None
    environment_options = dict(config["environment"])
    create_environment = load_function(environment_options.pop("factory"))
    replay = load_function(hook)
    checks_dir = Path(config["output_dir"]) / "_checks" / config["name"]
    if source is not None and checks_dir.resolve().is_relative_to(Path(source["trial_dir"]).parent.parent):
        raise ValueError("检查报告目录须位于原实验目录之外")
    checks_dir.mkdir(parents=True, exist_ok=True)
    output = Path(mkdtemp(prefix=f"{mode}-", dir=checks_dir))
    print(f"检查目录：{output}", flush=True)
    report_path = output / "report.json"
    report = {
        "schema_version": 1, "mode": mode, "status": "running", "model_calls": 0,
        "dataset_identity": dataset["package_identity"], "evaluator": config["evaluator"]["function"],
        "artifact_replay": hook, "environment": config["environment"], "source": source, "checks": [],
    }
    write_json(report_path, report)
    for task, condition, repeat, check_id in entries:
        check_dir = output / check_id
        check = {
            "task_id": task.id, "condition": condition, "repeat": repeat,
            "status": "running", "stage": "prepare", "reward": None, "passed": None,
            "metrics": {}, "errors": [], "output_dir": str(check_dir),
        }
        report["checks"].append(check)
        print(f"  {check_id}：{mode}", flush=True)
        started, environment = monotonic(), None
        try:
            prepared = prepare(task, check_dir / "task", condition)
            if not isinstance(prepared, PreparedTask):
                raise TypeError("数据集准备函数必须返回 evaluation.PreparedTask")
            check["stage"] = "environment"
            environment = create_environment(prepared.task_dir, output_dir=check_dir, **environment_options)
            await environment.start()
            context = TrialContext(task, prepared, environment, check_dir, condition, repeat)
            if setup is not None:
                check["stage"] = "setup"
                await setup(context)
            check["stage"] = "evaluate"
            score = await replay(context, artifacts)
            validate_score(score)
            check.update(reward=score.reward, metrics=score.metrics)
            if mode == "rescore":
                check["passed"] = score.reward >= threshold
            check["status"] = "completed"
        except asyncio.CancelledError:
            report["status"] = check["status"] = "cancelled"
            raise
        except Exception as exc:
            check["status"] = "error"
            check["errors"].append({"stage": check["stage"], "message": str(exc)})
        finally:
            try:
                if environment is not None:
                    await environment.destroy()
            except Exception as exc:
                check["status"] = "error"
                check["errors"].append({"stage": "cleanup", "message": str(exc)})
            check["duration_sec"] = monotonic() - started
            write_json(report_path, report)
    success = bool(report["checks"]) and all(check["status"] == "completed" for check in report["checks"])
    report["status"] = "completed" if success else "error"
    write_json(report_path, report)
    return report_path, success
