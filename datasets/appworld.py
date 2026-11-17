"""AppWorld 开发集资源适配；只暴露官方交互式 coding 操作和原生评分。"""

import hashlib
import json
from pathlib import Path
import shutil

from datasets.package import read_package_index, resource_path
from environment.appworld import APPWORLD_DATA_VERSION, APPWORLD_ROOT, APPWORLD_VERSION, AppWorldEnvironment
from evaluation.contracts import AgentResult, PreparedTask, Score, Task, TrialContext
from utils.json_io import write_json


TASK_FORMAT = "research-appworld-v1"


def resource_hashes(directory: Path) -> dict[str, str]:
    result = {}
    for path in sorted(directory.rglob("*")):
        relative = path.relative_to(directory).as_posix()
        checked = resource_path(directory, relative)
        if checked.is_file():
            result[relative] = hashlib.sha256(checked.read_bytes()).hexdigest()
    return result


def _check_sources(task: Task) -> None:
    package = read_package_index(task.source["index"], task_format=TASK_FORMAT)
    if package.identity() != task.source["package_identity"]:
        raise ValueError("AppWorld 资源包入口在生成计划后发生变化")
    for name in ("shared", "task"):
        if resource_hashes(Path(task.source[name])) != task.source[f"{name}_sha256"]:
            raise ValueError(f"AppWorld {name} 资源在生成计划后发生变化")


def load_tasks(index: Path, task_ids: list[str] | None = None) -> list[Task]:
    package = read_package_index(index, task_format=TASK_FORMAT)
    if package.metadata["id"] != "appworld" or package.metadata["provenance"]["package_version"] != APPWORLD_VERSION:
        raise ValueError(f"当前适配需要 AppWorld {APPWORLD_VERSION} 开发集资源包")
    shared = resource_path(package.root, package.index["shared"])
    if resource_hashes(shared) != package.index["shared_sha256"]:
        raise ValueError("AppWorld 公共资源与打包记录不一致")
    if (shared / "version.txt").read_text(encoding="utf-8").strip() != APPWORLD_DATA_VERSION:
        raise ValueError("AppWorld 公共数据版本与运行时不一致")
    dev_ids = set((shared / "datasets" / "dev.txt").read_text(encoding="utf-8").split())
    tasks = {}
    for entry in package.index["tasks"]:
        task_id = entry["id"]
        if task_id not in dev_ids:
            raise ValueError(f"首周适配只接受官方 dev 任务：{task_id}")
        task_dir = resource_path(package.root, entry["task"])
        if resource_hashes(task_dir) != entry["task_sha256"]:
            raise ValueError(f"AppWorld 任务资源与打包记录不一致：{task_id}")
        specs = json.loads((task_dir / "specs.json").read_text(encoding="utf-8"))
        if specs["db_version"] != APPWORLD_DATA_VERSION:
            raise ValueError(f"当前AppWorld运行时需要数据版本 {APPWORLD_DATA_VERSION}")
        instruction = specs["instruction"]
        supervisor = specs.get("supervisor", specs.get("main_user"))
        if not isinstance(instruction, str) or not instruction.strip() or not isinstance(supervisor, dict):
            raise ValueError(f"AppWorld 题目或用户信息缺失：{task_id}")
        # 与官方 task_to_dict 的可见字段一致，不把规格文件的其他用户字段交给模型。
        supervisor = {name: supervisor[name] for name in ("first_name", "last_name", "email", "phone_number")}
        prompt = (instruction + "\n\n## Runtime interface\n"
                  "Use execute_code for Python in the official persistent AppWorld shell. "
                  "The apis and requester objects are available. Discover API documentation with "
                  "apis.api_docs.show_app_descriptions(), then show_api_descriptions(app_name=...), "
                  "and show_api_doc(app_name=..., api_name=...). Print results to inspect them. "
                  "Variables persist between calls. After completing the requested changes, call "
                  "apis.supervisor.complete_task with an answer when the task requires one, then finish. "
                  "Shell/file tools and grading internals are unavailable.\n"
                  + "Supervisor: " + json.dumps(supervisor, ensure_ascii=False)
                  + "\nTask datetime: " + str(specs["datetime"]))
        tasks[task_id] = Task(
            id=task_id, instruction=prompt, agent_timeout_sec=300,
            metadata={"split": "dev", "package_version": APPWORLD_VERSION,
                      "native_instruction": instruction, "db_version": specs["db_version"]},
            source={"index": str(package.index_path), "package_identity": package.identity(),
                    "shared": str(shared), "task": str(task_dir),
                    "shared_sha256": package.index["shared_sha256"], "task_sha256": entry["task_sha256"]},
        )
    selected = list(tasks) if task_ids is None else task_ids
    if not selected or len(set(selected)) != len(selected):
        raise ValueError("任务清单不能为空或包含重复项")
    if missing := set(selected) - tasks.keys():
        raise ValueError(f"AppWorld 资源包没有这些任务：{sorted(missing)}")
    return [tasks[task_id] for task_id in selected]


def prepare_task(task: Task, destination: Path, condition: str) -> PreparedTask:
    if condition != "no-skill":
        raise ValueError("AppWorld 首周工程预跑仅支持 no-skill")
    _check_sources(task)
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=False)
    environment_dir = destination / "environment"
    environment_dir.mkdir()
    native_data = environment_dir / "data"
    shutil.copytree(task.source["shared"], native_data)
    shutil.copytree(task.source["task"], native_data / "tasks" / task.id)
    write_json(destination / "appworld-session.json", {
        "task_id": task.id, "instruction": task.metadata["native_instruction"],
    })
    import yaml
    from environment.tasks import prepare_docker_runtime

    config = {"metadata": {"benchmark": "AppWorld", "task_id": task.id},
              "agent": {"timeout_sec": task.agent_timeout_sec},
              "sandbox": {"workdir": APPWORLD_ROOT, "build_timeout_sec": 1800}}
    (destination / "task.md").write_text(
        "---\n" + yaml.safe_dump(config) + "---\n\n" + task.instruction + "\n", encoding="utf-8",
    )
    (environment_dir / "Dockerfile").write_text(
        "FROM python:3.11-slim\nWORKDIR /opt/appworld\n"
        f'RUN ["python", "-m", "pip", "install", "--no-cache-dir", "--index-url", "https://pypi.org/simple", "appworld=={APPWORLD_VERSION}"]\n'
        'RUN ["appworld", "install"]\nCOPY data /opt/appworld/data\n', encoding="utf-8",
    )
    (environment_dir / "docker-compose.yaml").write_text(
        'services:\n  main:\n    init: true\n'
        '    command: ["appworld", "serve", "environment", "--port", "9000"]\n'
        '    volumes:\n      - ${HOST_ARTIFACTS_PATH}:/opt/appworld/experiments/outputs\n', encoding="utf-8",
    )
    prepare_docker_runtime(destination, package_mirrors=False)
    return PreparedTask(task_dir=destination)


async def setup_environment(context: TrialContext) -> None:
    if not isinstance(context.environment, AppWorldEnvironment):
        raise TypeError("AppWorld 需要持续会话环境")
    actual_task = await context.environment.initialize_task()
    write_json(context.output_dir / "native-task.json", actual_task)


async def evaluate(context: TrialContext, agent: AgentResult) -> Score:
    if not isinstance(context.environment, AppWorldEnvironment):
        raise TypeError("AppWorld 原生评分需要本次持续会话")
    _check_sources(context.task)
    native = await context.environment.evaluate_task()
    write_json(context.output_dir / "native-evaluation.json", native)
    await context.environment.download(
        f"{APPWORLD_ROOT}/experiments/outputs/research/{context.task.id}",
        context.output_dir / "native-artifacts", directory=True,
    )
    if (type(native.get("success")) is not bool or type(native.get("num_tests")) is not int
            or native["num_tests"] <= 0 or not isinstance(native.get("passes"), list)
            or not isinstance(native.get("failures"), list)):
        raise ValueError("AppWorld 未产生有效原生评分，不记为零分")
    passes, failures, total = len(native["passes"]), len(native["failures"]), native["num_tests"]
    if passes + failures != total or native["success"] != (passes == total):
        raise ValueError("AppWorld 测试数量与成功状态不一致")
    return Score(reward=float(native["success"]), metrics={
        "native_success": native["success"], "test_pass_fraction": passes / total,
        "tests_passed": passes, "tests_total": total, "package_version": APPWORLD_VERSION,
        "db_version": context.task.metadata["db_version"], "split": "dev",
    })
