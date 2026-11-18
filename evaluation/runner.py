"""顺序执行试验，为每次试验提供独立环境并持久保存结果。"""

import asyncio
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime
from importlib.metadata import PackageNotFoundError, version
import json
import os
from pathlib import Path
import time
import traceback
from uuid import uuid4

from agent_session_analyzer.outcomes import trial_failure_type

from harness.runner import run_agent as run_harness

from .artifacts import redact, summarize, write_json, write_results
from .config import experiment_directory, load_function
from .contracts import PreparedTask, TrialContext, validate_score
from .experiment import (
    apply_task_exclusions, archive_trial, completed_trial, experiment_lock,
    iter_trials, load_run, skip_trial, trial_directory,
)


def _local_time() -> str:
    return datetime.now().astimezone().isoformat()


def _experiment_status(rows: dict, total: int) -> str:
    interrupted = len(rows) < total or any(
        row["status"] in {"running", "cancelled"} and not skip_trial(row)
        for row in rows.values()
    )
    failed = any(not completed_trial(row) for row in rows.values())
    return "interrupted" if interrupted else ("error" if failed else "completed")


@contextmanager
def _record_stage(row: dict, stage: str, result_path: Path, secret: str):
    """即使阶段失败或被取消，也保存实际经过的时间。"""
    started = time.monotonic()
    try:
        yield
    finally:
        row["stage_durations_sec"][stage] = time.monotonic() - started
        write_json(result_path, redact(row, secret))


def _versions() -> dict:
    found = {}
    for package in ("benchflow", "openhands-sdk", "deepseek-harness-sdk", "litellm"):
        try:
            found[package] = version(package)
        except PackageNotFoundError:
            found[package] = None
    return found


async def run_evaluation(config: dict, *, tasks=None, prepare_task=None,
                         setup_environment=None, run_agent=None, evaluate=None,
                         create_environment=None, resume: bool = False,
                         limit_new_trials: int | None = None, keep_failed: bool = False) -> Path:
    """通过传入函数或配置 module:function 替换任意组件。

    数据集：load(index, ids) -> list[Task]；prepare(task, destination, condition)
    -> PreparedTask。可选设置步骤：在 environment.start() 后调用异步 setup(context)。
    配置的任务只抽样一次；显式传入的任务视为已选定。
    智能体：公共 run_agent 调用配置的 execute(**native_options)。
    不向 harness 或其记录器传递评估对象。
    评分器：异步 (context, agent_result) -> Score。环境由外部工厂创建。
    resume=True 时归档忽略项并补足 sample_size，保留已有任务；跳过已完成评分和 agent 超时项。
    """
    with experiment_lock(experiment_directory(config)):
        return await _run_trials(
            config, tasks=tasks, prepare_task=prepare_task,
            setup_environment=setup_environment, run_agent=run_agent, evaluate=evaluate,
            create_environment=create_environment, resume=resume,
            limit_new_trials=limit_new_trials, keep_failed=keep_failed,
        )


async def _run_trials(config, *, tasks, prepare_task, setup_environment,
                      run_agent, evaluate, create_environment, resume, limit_new_trials, keep_failed):
    output = experiment_directory(config)
    dataset = config["dataset"]
    tasks, previous_manifest, rows = load_run(config, resume=resume, tasks=tasks)
    conditions, repeats = config["conditions"], config["repeats"]
    entries = list(iter_trials(tasks, conditions, repeats))
    total = len(entries)
    skipped = sum(skip_trial(row, keep_failed=keep_failed) for row in rows.values())
    print(f"实验目录：{output}\n计划试验数：{total}，跳过：{skipped}，待运行：{total - skipped}", flush=True)
    if resume and skipped == total:
        apply_task_exclusions(config, previous_manifest, tasks)
        # 修复结果已落盘、但汇总尚未来得及更新就退出的情况，无需模型凭据。
        write_results(output / "results.jsonl", list(rows.values()))
        write_json(output / "summary.json", summarize(list(rows.values()), conditions, len(tasks), repeats))
        previous_manifest.update(status=_experiment_status(rows, total), recorded_trials=total)
        write_json(output / "manifest.json", previous_manifest)
        print("没有需要重跑的试验；已完成项和 agent 超时项的记录保持原样。", flush=True)
        return output

    prepare_task = prepare_task or load_function(dataset["prepare"])
    if setup_environment is None and dataset.get("setup") is not None:
        setup_environment = load_function(dataset["setup"])
    run_agent = run_agent or load_function(config["agent"]["runner"])
    evaluate = evaluate or load_function(config["evaluator"]["function"])
    environment_options = dict(config["environment"])
    factory = environment_options.pop("factory", None)
    if create_environment is None:
        if factory is None:
            raise ValueError("请配置 environment.factory 或传入 create_environment")
        create_environment = load_function(factory)
    agent_options = dict(config["agent"])
    agent_options.pop("runner", None)
    recorder = agent_options.pop("recorder", None)
    tools = agent_options.pop("tools", None)
    key_name = config["model"]["api_key_env"]
    secret = os.environ.get(key_name)
    if not secret:
        raise ValueError(f"运行前请设置模型凭据环境变量 {key_name}。")

    components = {
        "prepare": f"{prepare_task.__module__}:{prepare_task.__qualname__}",
        "setup": (f"{setup_environment.__module__}:{setup_environment.__qualname__}"
                  if setup_environment is not None else None),
        "agent": f"{run_agent.__module__}:{run_agent.__qualname__}",
        "recorder": recorder,
        "evaluator": f"{evaluate.__module__}:{evaluate.__qualname__}",
        "environment": f"{create_environment.__module__}:{create_environment.__qualname__}",
    }
    if resume:
        if previous_manifest.get("components") != components:
            raise ValueError("续跑组件与原实验不一致，请使用原组件或更换实验名称")
        apply_task_exclusions(config, previous_manifest, tasks)
        manifest = previous_manifest
        manifest["recorded_trials"] = len(rows)
        manifest["resumed_at"] = _local_time()
        manifest["resume_versions"] = _versions()
        manifest.pop("finished_at", None)
    else:
        try:
            output.mkdir(parents=True)
        except FileExistsError as exc:
            raise FileExistsError(
                f"实验目录已存在：{output}。"
                "续跑请加 --resume；新实验请通过 --name 或 config.name 更换名称。"
            ) from exc
        manifest = {
            "schema_version": 1, "started_at": _local_time(), "config": config,
            "experiment_id": uuid4().hex, "experiment_name": config["name"],
            "versions": _versions(), "planned_trials": total,
            "tasks": [asdict(task) for task in tasks], "components": components,
        }
    experiment_id = manifest["experiment_id"]
    manifest["status"] = "running"
    write_json(output / "manifest.json", manifest)
    # 从各试验结果重建索引，恢复中断写入并去除以往的重复记录。
    write_results(output / "results.jsonl", list(rows.values()))
    write_json(output / "summary.json", summarize(list(rows.values()), conditions, len(tasks), repeats))

    started_trials = 0
    try:
        for trial_number, (task, condition, repeat, trial_id) in enumerate(entries, 1):
            if skip_trial(rows.get(trial_id), keep_failed=keep_failed):
                reason = "已完成" if completed_trial(rows[trial_id]) else "保留已有失败记录"
                print(f"[{trial_number}/{total}] {trial_id}：{reason}，跳过", flush=True)
                continue
            if limit_new_trials is not None and started_trials >= limit_new_trials:
                break
            started_trials += 1
            if resume:
                archived = archive_trial(output, trial_id)
                if archived is not None:
                    rows.pop(trial_id, None)
                    print(f"  {trial_id}：旧尝试已归档至 {archived}", flush=True)
            trial_dir = trial_directory(output, trial_id)
            trial_dir.mkdir(parents=True)
            result_path = trial_dir / "result.json"
            started = time.monotonic()
            row = {
                "schema_version": 1, "trial_id": trial_id,
                "task_id": task.id, "condition": condition, "repeat": repeat,
                "model": config["model"]["model"], "started_at": _local_time(),
                "dataset_index": dataset["index"],
                "agent_runner": manifest["components"]["agent"],
                "evaluator": manifest["components"]["evaluator"],
                "status": "running", "reward": None, "passed": None,
                "metrics": {}, "agent": None, "errors": [],
                "stage_durations_sec": dict.fromkeys((
                    "prepare", "environment", "setup", "agent", "evaluate", "cleanup",
                )),
            }
            write_json(result_path, row)
            rows[trial_id] = redact(row, secret)
            stage, environment = "prepare", None
            print(f"[{trial_number}/{total}] {trial_id}：准备任务", flush=True)
            try:
                # 准备任务
                with _record_stage(row, stage, result_path, secret):
                    prepared = prepare_task(task, trial_dir / "task", condition)
                    if not isinstance(prepared, PreparedTask):
                        raise TypeError("数据集准备函数必须返回 evaluation.PreparedTask")
                    write_json(trial_dir / "task-info.json", {
                        "task_id": task.id, "source": task.source,
                        "skill_catalog": prepared.skill_catalog,
                    })

                # 初始化环境
                stage = "environment"
                with _record_stage(row, stage, result_path, secret):
                    environment = create_environment(
                        prepared.task_dir, output_dir=trial_dir,
                        **environment_options,
                    )
                    row["environment_id"] = getattr(environment, "run_id", None)
                    await environment.start()
                    context = TrialContext(task, prepared, environment, trial_dir, condition, repeat)
                
                # 设置环境
                stage = "setup"
                if setup_environment is not None:
                    with _record_stage(row, stage, result_path, secret):
                        await setup_environment(context)

                # 智能体运行
                stage = "agent"
                print(f"  {trial_id}：运行智能体", flush=True)
                with _record_stage(row, stage, result_path, secret):
                    agent_result = await run_harness(
                        runner=run_agent,
                        recorder=recorder,
                        instruction=task.instruction,
                        model=config["model"],
                        tools=tools,
                        settings=dict(agent_options),
                        environment=environment,
                        output_dir=trial_dir / "agent",
                        timeout_sec=task.agent_timeout_sec,
                        skill_catalog=prepared.skill_catalog,
                        metadata={
                            "experiment_id": experiment_id, "experiment_name": config["name"],
                            "trial_id": trial_id, "task_id": task.id,
                            "condition": condition, "repeat": repeat,
                        },
                    )
                    row["agent"] = asdict(agent_result)

                #评估任务结果
                stage = "evaluate"
                print(f"  {trial_id}：评估结果", flush=True)
                with _record_stage(row, stage, result_path, secret):
                    score = await evaluate(context, agent_result)
                    validate_score(score)
                    row.update(reward=float(score.reward), metrics=score.metrics,
                               passed=score.reward >= config["pass_threshold"])
            except BaseException as exc:
                row["status"] = "cancelled" if isinstance(exc, (asyncio.CancelledError, KeyboardInterrupt)) else "error"
                row["errors"].append({"stage": stage, "type": type(exc).__name__, "message": redact(str(exc), secret)})
                (trial_dir / "error.txt").write_text(redact(traceback.format_exc(), secret), encoding="utf-8")
                if not isinstance(exc, Exception):
                    raise
            finally:
                # 清理环境
                cleanup_interrupt = None
                if environment is not None:
                    try:
                        with _record_stage(row, "cleanup", result_path, secret):
                            await environment.destroy()
                    except BaseException as exc:
                        row["status"] = "cancelled" if isinstance(exc, (asyncio.CancelledError, KeyboardInterrupt)) else "error"
                        row["errors"].append({"stage": "cleanup", "type": type(exc).__name__, "message": redact(str(exc), secret)})
                        if not isinstance(exc, Exception):
                            # 传播清理阶段的取消异常前，先保存本次试验。
                            cleanup_interrupt = exc
                if row["status"] == "running":
                    row["status"] = "completed"
                partial_agent = trial_dir / "agent" / "result.json"
                if row["agent"] is None and partial_agent.is_file():
                    row["agent"] = json.loads(partial_agent.read_text(encoding="utf-8"))
                trace_path = (row["agent"] or {}).get("trace_path")
                if trace_path:
                    path = Path(trace_path)
                    if not path.is_absolute():
                        path = trial_dir / path
                    path = path.resolve()
                    base = trial_dir.resolve()
                    row["trace_path"] = path.relative_to(base).as_posix() if path.is_relative_to(base) else str(path)
                row["failure_type"] = trial_failure_type(row)
                row.update(finished_at=_local_time(), duration_sec=time.monotonic() - started)
                # 仅清理失败时奖励仍然有效，失败情况由状态字段体现。
                safe_row = redact(row, secret)
                write_json(result_path, safe_row)
                rows[trial_id] = safe_row
                write_results(output / "results.jsonl", list(rows.values()))
                write_json(output / "summary.json", summarize(list(rows.values()), conditions, len(tasks), repeats))
                status_text = {"completed": "已完成", "cancelled": "已取消", "error": "错误"}[row["status"]]
                print(f"  {trial_id}：{status_text}，奖励={row['reward']}", flush=True)
                if cleanup_interrupt is not None:
                    raise cleanup_interrupt
    finally:
        # 保存结果
        manifest["finished_at"] = _local_time()
        manifest["recorded_trials"] = len(rows)
        manifest["status"] = _experiment_status(rows, total)
        write_json(output / "manifest.json", manifest)
        write_results(output / "results.jsonl", list(rows.values()))
        write_json(output / "summary.json", summarize(list(rows.values()), conditions, len(tasks), repeats))
        print(f"结果已保存：{output}", flush=True)
    return output
