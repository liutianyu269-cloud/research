"""通过 --dataset、--environment、--agent、--evaluation 显式组合实验。"""

import argparse
import asyncio
import json
from pathlib import Path

from .config import experiment_directory, load_config
from .experiment import (
    completed_trial, ignored_trial_directories, iter_trials, load_run, skip_trial,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="在隔离的任务环境中评估智能体")
    parser.add_argument("--dataset", type=Path, required=True, help="数据集 TOML 文件")
    parser.add_argument("--environment", type=Path, required=True, help="执行环境 TOML 文件")
    parser.add_argument("--agent", type=Path, required=True, help="Agent 与模型 TOML 文件")
    parser.add_argument("--evaluation", type=Path, required=True, help="测试条件与评分 TOML 文件")
    parser.add_argument("--name", required=True, help="实验名称，支持中文；续跑时使用原名称")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--plan", action="store_true", help="仅读取配置和任务，不调用模型或启动 Docker")
    mode.add_argument("--preflight", action="store_true", help="不调用模型，检查任务环境和原生评分器")
    mode.add_argument("--rescore-from", type=Path, metavar="TRIAL_DIR",
                      help="不调用模型，用旧试验的产物重新运行原生评分")
    parser.add_argument("--resume", action="store_true", help="续跑同名实验，归档忽略项并补抽，跳过已完成和 agent 超时项，重跑其余未完成项")
    parser.add_argument("--task", nargs="+", help="覆盖 dataset.task_ids")
    args = parser.parse_args()
    if args.resume and (args.preflight or args.rescore_from is not None):
        parser.error("--preflight、--rescore-from 不能与 --resume 同用")
    if args.rescore_from is not None and args.task is not None:
        parser.error("--rescore-from 使用原试验的题目，不能与 --task 同用")
    config = load_config(
        dataset=args.dataset, environment=args.environment, agent=args.agent,
        evaluation=args.evaluation, name=args.name,
    )
    if args.task is not None:
        config["dataset"]["task_ids"] = args.task
    output = experiment_directory(config)
    dataset = config["dataset"]
    
    if args.plan:
        tasks, manifest, results = load_run(config, resume=args.resume)
        pending = [trial_id for _, _, _, trial_id in iter_trials(tasks, config["conditions"], config["repeats"])
                   if not skip_trial(results.get(trial_id))]
        saved_ids = {task["id"] for task in manifest["tasks"]} if manifest is not None else set()
        replacements = [task.id for task in tasks if task.id not in saved_ids] if args.resume else []
        print(json.dumps({
            "name": config["name"], "model": config["model"]["model"],
            "tasks": [task.id for task in tasks], "conditions": config["conditions"],
            "repeats": config["repeats"],
            "sample_size": dataset.get("sample_size"), "seed": dataset.get("seed"),
            "exclude_task_ids": dataset.get("exclude_task_ids", []),
            "planned_trials": len(tasks) * len(config["conditions"]) * config["repeats"],
            "resume": args.resume,
            "replacement_task_ids": replacements,
            "ignored_trial_ids_to_archive": [trial_id for trial_id, _ in ignored_trial_directories(config, manifest)],
            "ignored_trials_dir": str(output / "ignored_trials"),
            "skipped_trials": sum(skip_trial(row) for row in results.values()),
            "skipped_agent_timeout_trial_ids": [trial_id for trial_id, row in results.items()
                                                if skip_trial(row) and not completed_trial(row)],
            "pending_trials": len(pending), "pending_trial_ids": pending,
            "output_dir": config["output_dir"],
            "experiment_dir": str(output),
            "agent_runner": config["agent"]["runner"], "evaluator": config["evaluator"]["function"],
            "agent_recorder": config["agent"].get("recorder"),
            "tools": config["agent"].get("tools"),
            "dataset_loader": dataset["loader"], "dataset_prepare": dataset["prepare"],
            "dataset_package": dataset["package"],
            "dataset_identity": dataset["package_identity"],
            "dataset_setup": dataset.get("setup"),
            "environment_factory": config["environment"]["factory"],
        }, ensure_ascii=False, indent=2))
        return 0
    if args.preflight or args.rescore_from is not None:
        from .checks import run_artifact_checks

        try:
            report, success = asyncio.run(run_artifact_checks(config, source_trial=args.rescore_from))
        except (ValueError, OSError) as exc:
            parser.exit(1, f"无法开始检查：{exc}\n")
        print(f"检查报告：{report}")
        return 0 if success else 1
    # 遵循现有 harness 约定，环境变量中的值优先。
    from dotenv import load_dotenv
    from .runner import run_evaluation

    load_dotenv(Path.cwd() / ".env", override=False)
    output = asyncio.run(run_evaluation(config, resume=args.resume))
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    return 0 if manifest["status"] == "completed" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
