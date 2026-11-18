"""读取命令行指定的组件 TOML，组合并校验实验配置。"""

from pathlib import Path
import re
import tomllib

from datasets.package import read_package
from tools.loader import validate_tools
from harness.runner import load_function


_COMPONENT_KEYS = {
    "dataset": {"dataset"},
    "environment": {"environment"},
    "agent": {"agent", "model"},
    "evaluation": {"output_dir", "conditions", "repeats", "pass_threshold", "evaluator"},
}


def _read_toml(path: Path) -> dict:
    """先按字段所在文件解析路径，避免组件移动后改变相对路径含义。"""
    try:
        config = tomllib.loads(path.read_text(encoding="utf-8-sig"))
    except tomllib.TOMLDecodeError as exc:
        raise ValueError(f"TOML 配置格式错误：{path}：{exc}") from exc
    path_fields = [(config, "output_dir")]
    dataset = config.get("dataset")
    if isinstance(dataset, dict):
        path_fields.append((dataset, "package"))
    for section, key in path_fields:
        if key not in section:
            continue
        value = section[key]
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{path} 中的 {key} 必须为非空路径字符串")
        # 完整配置校验时再读取资源包。
        section[key] = str((path.parent / value).resolve())
    return config


def function_reference(value, name: str) -> None:
    if (not isinstance(value, str)
            or not re.fullmatch(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*:[A-Za-z_]\w*", value)):
        raise ValueError(f"{name} 必须为 module:function 引用")


def _directory_component(value, name: str) -> str:
    """保留可读名称，同时拒绝路径穿越和 Windows 无效名称。"""
    if (not isinstance(value, str) or not value or value != value.strip()
            or value in {".", ".."} or value.endswith(".")
            or re.search(r'[<>:"/\\|?*\x00-\x1f]', value)):
        raise ValueError(f"{name} 必须为非空目录名，不能包含路径分隔符、"
                         "无效文件名字符、首尾空格或末尾句点")
    if re.fullmatch(r"(?:CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³])(?:\..*)?", value, re.IGNORECASE):
        raise ValueError(f"{name} 不能使用 Windows 保留设备名称：{value!r}")
    return value


def experiment_directory(config: dict) -> Path:
    """解析 output_dir/benchmark/harness/model/name 路径，不创建文件。"""
    name = _directory_component(config["name"], "实验名称")
    dataset_module = config["dataset"]["loader"].partition(":")[0]
    benchmark = _directory_component(dataset_module.rsplit(".", 1)[-1], "基准目录")
    runner_module = config["agent"]["runner"].partition(":")[0]
    harness = _directory_component(
        runner_module.removesuffix(".runner").rsplit(".", 1)[-1], "Harness 目录",
    )
    model = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "-", config["model"]["model"])
    model = _directory_component(model, "模型目录")
    return Path(config["output_dir"]) / benchmark / harness / model / name


def load_config(*, dataset: Path, environment: Path, agent: Path,
                evaluation: Path, name: str) -> dict:
    """显式选择四个组件文件和实验名，返回调度与快照共用的配置字典。"""
    component_paths = {
        "dataset": dataset, "environment": environment,
        "agent": agent, "evaluation": evaluation,
    }
    config = {"name": name}
    for component_name, component_path in component_paths.items():
        component_path = Path(component_path).resolve(strict=True)
        component = _read_toml(component_path)
        allowed = _COMPONENT_KEYS[component_name]
        if extra := component.keys() - allowed:
            raise ValueError(
                f"{component_path} 包含不属于 {component_name} 组件的配置项：{sorted(extra)}"
            )
        if component_name == "evaluation":
            component.setdefault("output_dir", str((component_path.parent / "../logs/evaluation").resolve()))
        # 各组件负责的顶层字段互不重叠，无需递归合并或覆盖规则。
        config.update(component)
    for section in ("dataset", "model", "agent", "evaluator", "environment"):
        if not isinstance(config.get(section), dict):
            raise ValueError(f"{section} 必须在对应组件文件中定义为配置表")
    _directory_component(config["name"], "实验名称")
    config.setdefault("repeats", 1)
    if type(config["repeats"]) is not int or config["repeats"] < 1:
        raise ValueError("repeats 必须为正整数")
    conditions = config.setdefault("conditions", ["default"])
    if (not isinstance(conditions, list) or not conditions
            or any(not isinstance(item, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", item)
                   for item in conditions)
            or len(conditions) != len(set(conditions))):
        raise ValueError("conditions 必须包含互不重复的有效路径组成部分")
    threshold = config.setdefault("pass_threshold", 1.0)
    if isinstance(threshold, bool) or not isinstance(threshold, (float, int)) or not 0 <= threshold <= 1:
        raise ValueError("pass_threshold 必须在 [0, 1] 范围内")
    dataset = config["dataset"]
    if extra := dataset.keys() - {"package", "task_ids", "exclude_task_ids", "sample_size", "seed", "loader", "prepare", "setup"}:
        raise ValueError(f"未知数据集配置项：{sorted(extra)}")
    package_path = dataset.get("package")
    if not isinstance(package_path, str) or not package_path.strip():
        raise ValueError("dataset.package 必须指定标准资源包目录")
    package = read_package(package_path)
    dataset["package"] = str(package.root)
    dataset["index"] = str(package.index_path)
    dataset["package_identity"] = package.identity()
    if "task_ids" in dataset and (not isinstance(dataset["task_ids"], list)
                                or not all(isinstance(item, str) for item in dataset["task_ids"])):
        raise ValueError("dataset.task_ids 必须为任务 ID 列表")
    for key in ("loader", "prepare"):
        function_reference(dataset.get(key), f"dataset.{key}")
    if dataset.get("setup") is not None:
        function_reference(dataset["setup"], "dataset.setup")
    model = config["model"]
    if "api_key" in model:
        raise ValueError("请将模型 API 密钥存入环境变量，并使用 api_key_env 指定")
    if not isinstance(model.get("model"), str) or not model["model"].strip():
        raise ValueError("model.model 不能为空")
    if not isinstance(model.get("api_key_env"), str) or not model["api_key_env"].strip():
        raise ValueError("model.api_key_env 必须指定环境变量名称")
    agent = config.setdefault("agent", {})
    function_reference(agent.get("runner"), "agent.runner")
    if "recorder" in agent:
        function_reference(agent["recorder"], "agent.recorder")
    if "tools" in agent:
        agent["tools"] = validate_tools(agent["tools"])
    if "usage" in agent:
        raise ValueError("请删除旧的 agent.usage，并在 [agent] 下设置 cost_tracking = true/false")
    cost_tracking = agent.get("cost_tracking", False)
    if type(cost_tracking) is not bool:
        raise ValueError("agent.cost_tracking 必须为 true/false 布尔开关")
    if cost_tracking and not agent.get("recorder"):
        raise ValueError("启用 agent.cost_tracking 需要配置 agent.recorder")
    evaluator = config.setdefault("evaluator", {})
    if extra := evaluator.keys() - {"function", "artifact_replay"}:
        raise ValueError(f"未知评分器配置项：{sorted(extra)}")
    function_reference(evaluator.get("function"), "evaluator.function")
    if "artifact_replay" in evaluator:
        function_reference(evaluator["artifact_replay"], "evaluator.artifact_replay")
    environment = config.setdefault("environment", {})
    function_reference(environment.get("factory"), "environment.factory")
    return config
