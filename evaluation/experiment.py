"""实验计划恢复、试验状态读取及旧尝试归档，不启动执行后端。"""

from contextlib import contextmanager
from dataclasses import asdict
import json
import math
import os
from pathlib import Path
import re
from uuid import uuid4

from agent_session_analyzer.outcomes import trial_failure_type

from .config import experiment_directory
from .contracts import Task
from .dataset import excluded_task_ids, load_tasks


def iter_trials(tasks, conditions, repeats):
    """按原有任务、重复次数、实验条件顺序生成稳定的试验标识。"""
    for task in tasks:
        for repeat in range(1, repeats + 1):
            for condition in conditions:
                yield task, condition, repeat, f"{task.id}__{condition}__{repeat:03d}"


def completed_trial(result: dict | None) -> bool:
    """流程完成且已有合法评分即可跳过；零分不属于执行失败。"""
    if result is None:
        return False
    reward = result.get("reward")
    return (result.get("status") == "completed" and not result.get("errors")
            and not isinstance(reward, bool) and isinstance(reward, (int, float))
            and math.isfinite(reward) and 0 <= reward <= 1)


def skip_trial(result: dict | None, *, keep_failed: bool = False) -> bool:
    """续跑保留已有合法评分及已耗尽 agent 时间预算的最终记录。"""
    if keep_failed and result and result.get("status") in {"error", "completed", "cancelled"}:
        return True
    return completed_trial(result) or bool(
        result and result.get("status") in {"error", "completed", "cancelled"}
        and trial_failure_type(result) == "agent_timeout"
    )


def _read_object(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"无法读取实验记录：{path}：{exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"实验记录必须为 JSON 对象：{path}")
    return value


def trial_directory(output: Path, trial_id: str) -> Path:
    """拒绝链接或越界目录，避免归档时移动其他实验的文件。"""
    directory = output / "trials" / trial_id
    for path in (directory.parent, directory):
        if path.is_symlink() or path.is_junction():
            raise ValueError(f"试验目录不能为链接：{path}")
    if not directory.resolve().is_relative_to(output.resolve()):
        raise ValueError(f"试验目录超出实验范围：{directory}")
    return directory


def _resume_identity(config: dict) -> dict:
    """忽略列表可以调整，其余配置仍用于校验同名实验身份。"""
    dataset = dict(config["dataset"])
    dataset.pop("exclude_task_ids", None)
    evaluator = dict(config["evaluator"])
    # 产物回放只在独立检查命令使用，不影响历史实验续跑。
    evaluator.pop("artifact_replay", None)
    return {**config, "dataset": dataset, "evaluator": evaluator}


def _task_history(manifest: dict) -> list[dict]:
    """合并最初清单和历次活动清单，保留曾抽到任务的定义及顺序。"""
    known_tasks = {}
    for task in (manifest.get("original_tasks", [])
                 + manifest.get("task_history", []) + manifest["tasks"]):
        known_tasks.setdefault(task["id"], task)
    return list(known_tasks.values())


def load_run(config: dict, *, resume=False, tasks=None) -> tuple[list[Task], dict | None, dict]:
    """返回任务、原实验清单及按试验 ID 索引的结果；本函数只读文件。

    续跑保留 manifest 的活动任务，排除忽略项后补足 sample_size。各 trial/result.json
    是恢复依据，包括尚未来得及写入 results.jsonl 的最终结果。
    """
    output = experiment_directory(config)
    manifest = None
    if resume:
        manifest = _read_object(output / "manifest.json")
        if manifest.get("schema_version") != 1 or not manifest.get("experiment_id"):
            raise ValueError("续跑需要 schema_version=1 且包含 experiment_id 的实验记录")
        saved_config = manifest.get("config")
        if not isinstance(saved_config, dict):
            raise ValueError("原实验缺少配置快照，无法安全续跑")
        saved_identity = _resume_identity(saved_config)
        current_identity = _resume_identity(config)
        if saved_identity != current_identity:
            changed = sorted(key for key in saved_identity.keys() | current_identity.keys()
                             if saved_identity.get(key) != current_identity.get(key))
            raise ValueError(f"续跑配置与原实验不一致：{', '.join(changed)}；仅允许调整 dataset.exclude_task_ids")
        saved_tasks = manifest.get("original_tasks", manifest.get("tasks"))
        active_tasks = manifest.get("tasks")
        if not isinstance(saved_tasks, list) or not saved_tasks or not isinstance(active_tasks, list):
            raise ValueError("原实验缺少实际任务清单，无法续跑")
        expected = len(active_tasks) * len(config["conditions"]) * config["repeats"]
        if manifest.get("planned_trials") != expected:
            raise ValueError("原实验的计划试验数与任务清单不一致")
        if tasks is not None and [asdict(task) for task in tasks] != saved_tasks:
            raise ValueError("续跑时显式传入的 tasks 必须与原实验任务清单一致")
        tasks = [Task(**task) for task in active_tasks]
    elif tasks is None:
        tasks = load_tasks(config["dataset"])
    tasks = list(tasks)
    if resume:
        previous_ids = {task["id"] for task in _task_history(manifest)}
        tasks = load_tasks(config["dataset"], retained_tasks=tasks, previous_task_ids=previous_ids)
    ids = [task.id for task in tasks]
    if ((not ids and not resume) or len(set(ids)) != len(ids)
            or any(not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", value)
                   for value in ids)):
        raise ValueError("任务 ID 必须唯一、非空，且可用作路径组成部分")
    entries = list(iter_trials(tasks, config["conditions"], config["repeats"]))
    if len({entry[3] for entry in entries}) != len(entries):
        raise ValueError("任务 ID 与实验条件组合产生了重复试验 ID")
    results = {}
    if resume:
        for task, condition, repeat, trial_id in entries:
            path = trial_directory(output, trial_id) / "result.json"
            if not path.exists():
                continue
            result = _read_object(path)
            identity = {"trial_id": trial_id, "task_id": task.id, "condition": condition, "repeat": repeat}
            if any(result.get(key) != value for key, value in identity.items()):
                raise ValueError(f"试验结果与目录标识不一致：{path}")
            if (result.get("status") not in {"running", "completed", "error", "cancelled"}
                    or not isinstance(result.get("errors"), list)
                    or "reward" not in result or "passed" not in result):
                raise ValueError(f"试验结果缺少有效的状态或评分字段：{path}")
            reward = result["reward"]
            if reward is not None and (isinstance(reward, bool) or not isinstance(reward, (int, float))
                                       or not math.isfinite(reward) or not 0 <= reward <= 1):
                raise ValueError(f"试验评分无效，请检查原始结果：{path}")
            results[trial_id] = result
    return tasks, manifest, results


def ignored_trial_directories(config: dict, manifest: dict | None) -> list[tuple[str, Path]]:
    """列出仍在 trials 下的忽略项，供只读计划和实际归档共用。"""
    if manifest is None:
        return []
    excluded = excluded_task_ids(config["dataset"])
    tasks = [Task(**task) for task in _task_history(manifest) if task["id"] in excluded]
    output = experiment_directory(config)
    directories = []
    for _, _, _, trial_id in iter_trials(tasks, config["conditions"], config["repeats"]):
        directory = trial_directory(output, trial_id)
        if directory.exists():
            if not directory.is_dir():
                raise ValueError(f"试验路径必须为目录：{directory}")
            directories.append((trial_id, directory))
    return directories


def apply_task_exclusions(config: dict, manifest: dict, tasks: list[Task]) -> None:
    """在实验锁内归档忽略项，并更新待持久化的活动任务清单。"""
    output = experiment_directory(config)
    directories = ignored_trial_directories(config, manifest)
    for trial_id, _ in directories:
        destination = archive_trial(output, trial_id, archive_directory="ignored_trials")
        if destination is not None:
            manifest.setdefault("ignored_trial_archives", []).append({
                "trial_id": trial_id, "path": destination.relative_to(output).as_posix(),
            })
            print(f"  {trial_id}：忽略，已归档至 {destination}", flush=True)
    history = _task_history(manifest)
    active_tasks = [asdict(task) for task in tasks]
    if active_tasks != manifest["tasks"]:
        manifest.setdefault("original_tasks", manifest["tasks"])
        known_ids = {task["id"] for task in history}
        for task in active_tasks:
            if task["id"] not in known_ids:
                history.append(task)
                known_ids.add(task["id"])
                print(f"  补抽任务：{task['id']}", flush=True)
        manifest["task_history"] = history
    manifest.update(
        config=config, tasks=active_tasks,
        planned_trials=len(tasks) * len(config["conditions"]) * config["repeats"],
    )


def archive_trial(output: Path, trial_id: str, *, archive_directory: str = "attempts") -> Path | None:
    """归档完整 trial；重跑项放 attempts，忽略项放独立的 ignored_trials。"""
    if archive_directory not in {"attempts", "ignored_trials"}:
        raise ValueError(f"不支持的归档目录：{archive_directory}")
    source = trial_directory(output, trial_id)
    if not source.exists():
        return None
    destination = output / archive_directory / trial_id / uuid4().hex
    for path in (destination.parent.parent, destination.parent):
        if path.is_symlink() or path.is_junction():
            raise ValueError(f"归档目录不能为链接：{path}")
    if not destination.resolve().is_relative_to(output.resolve()):
        raise ValueError(f"归档目录超出实验范围：{destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    source.rename(destination)
    return destination


@contextmanager
def experiment_lock(output: Path):
    """独占同名实验；操作系统会在进程终止时释放锁，锁文件本身保留。"""
    output.parent.mkdir(parents=True, exist_ok=True)
    # 锁放在实验目录旁，新实验的参数校验失败时不会留下空实验目录。
    lock_path = output.with_name(f".{output.name}.lock")
    with lock_path.open("a+b") as stream:
        if os.name == "nt":
            import msvcrt

            stream.seek(0)
            try:
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise RuntimeError(f"实验正由其他进程运行或无法获取锁：{output}") from exc
        else:
            import fcntl

            try:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise RuntimeError(f"实验正由其他进程运行或无法获取锁：{output}") from exc
        try:
            yield
        finally:
            if os.name == "nt":
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
