"""SkillGenBench 工程预跑：保留原题与评分，隔离作答和评分资料。"""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
import re
import shutil
import tomllib

from datasets.package import read_package_index, resource_path
from evaluation.contracts import AgentResult, PreparedTask, Score, Task, TrialContext


TASK_FORMAT = "research-skillgenbench-v1"
UPSTREAM_REVISION = "5a8bd61d8191e34fa1bbbffbff7f70db1d2a027d"


@dataclass(frozen=True)
class TaskProfile:
    repo: str
    runtime: str
    packages: tuple[str, ...]
    imports: str


TASK_PROFILES = {
    "PyPDF2_gtb03": TaskProfile("pypdf2", "pypdf-minimal", ("pypdf==5.5.0",), "import pypdf"),
    "PyPDF2_gen01": TaskProfile("pypdf2", "pypdf-page-range",
                                ("pypdf==5.5.0", "PyPDF2==3.0.1"), "import pypdf, PyPDF2"),
    "SoundFile_gen03": TaskProfile("soundfile", "soundfile-mono",
                                   ("soundfile==0.13.1", "numpy==2.2.6"), "import soundfile, numpy"),
}
DEFAULT_TASK_ID = "PyPDF2_gtb03"


def check_grader(bundle: Path, upstream: dict) -> None:
    """在启动模型前核对所支持的上游评分入口与参考文件。"""
    tests = resource_path(bundle, upstream["validation"]["tests_dir"])
    runner = resource_path(bundle, upstream["validation"]["runner"])
    if runner != tests / "test.sh" or not runner.is_file():
        raise ValueError(f"不支持的 SkillGenBench 评分入口：{runner}")
    context = resource_path(bundle, "context")
    reference = resource_path(context, upstream["evaluation"]["reference_relpath"])
    groundtruth = resource_path(bundle, upstream["context"]["groundtruth_dir"])
    if not reference.is_relative_to(groundtruth) or not reference.is_file():
        raise ValueError(f"参考文件须位于 groundtruth 中：{reference}")
    for script in tests.rglob("*.py"):
        try:
            compile(script.read_bytes(), str(script), "exec")
        except SyntaxError as exc:
            raise ValueError(f"原生评分脚本无法解析：{script}：{exc.msg}") from exc


def _snapshot(directory: Path) -> dict[str, str]:
    hashes = {}
    for path in sorted(directory.rglob("*")):
        if path.is_symlink() or path.is_junction():
            raise ValueError(f"任务资源不能包含链接：{path}")
        if path.is_file():
            hashes[path.relative_to(directory).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes


def _check_sources(task: Task) -> None:
    package = read_package_index(task.source["index"], task_format=TASK_FORMAT)
    if package.identity() != task.source["package_identity"]:
        raise ValueError("计划生成后，SkillGenBench 资源包描述或索引发生了变化")
    for key in ("bundle", "docs"):
        if _snapshot(Path(task.source[key])) != task.source[f"{key}_sha256"]:
            raise ValueError(f"计划生成后，SkillGenBench 的 {key} 资料发生了变化")


def load_tasks(index: Path, task_ids: list[str] | None = None) -> list[Task]:
    """读取标准资源包；运行时无需访问原始 Git 仓库或包外文件。"""
    package = read_package_index(index, task_format=TASK_FORMAT)
    revision = package.metadata["provenance"]["revision"]
    if package.metadata["id"] != "skillgenbench" or revision != UPSTREAM_REVISION:
        raise ValueError(f"需要 SkillGenBench 提交 {UPSTREAM_REVISION} 的资源包")
    tasks = {}
    entries = {entry["id"]: entry for entry in package.index["tasks"]}
    selected = list(entries) if task_ids is None else task_ids
    if not selected or len(set(selected)) != len(selected):
        raise ValueError("任务选择不能为空或包含重复项")
    if unknown := set(selected) - entries.keys():
        raise ValueError(f"索引中没有任务：{sorted(unknown)}")
    for task_id in selected:
        entry = entries[task_id]
        bundle = resource_path(package.root, entry["bundle"])
        docs = resource_path(package.root, entry["docs"])
        hashes = {}
        for key, directory in (("bundle", bundle), ("docs", docs)):
            hashes[key] = _snapshot(directory) if directory.is_dir() else None
            if hashes[key] is None or hashes[key] != entry[f"{key}_sha256"]:
                raise ValueError(f"资源包 {entry['id']} 的 {key} 与打包时的哈希不一致")
        upstream = tomllib.loads((bundle / "task.toml").read_text(encoding="utf-8-sig"))
        if upstream["task"]["task_id"] != task_id:
            raise ValueError("任务文件与资源包索引中的 ID 不一致")
        if not isinstance(task_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", task_id):
            raise ValueError(f"无效的任务 ID：{task_id!r}")
        profile = TASK_PROFILES.get(task_id)
        if (profile is None or upstream["task"]["status"] != "enabled"
                or upstream["task"]["repo_slug"] != profile.repo
                or upstream["runtime"]["docker_image"] != "light"
                or upstream["runtime"]["needs_reference_repo"] is not False):
            raise ValueError(f"当前工程预跑不支持该任务或其运行要求：{task_id}")
        check_grader(bundle, upstream)
        instruction = (bundle / "instruction.md").read_text(encoding="utf-8-sig").strip()
        if not instruction:
            raise ValueError(f"任务指令为空：{task_id}")
        tasks[task_id] = Task(
            id=task_id, instruction=instruction, agent_timeout_sec=300,
            metadata={"upstream": upstream, "revision": revision,
                      "runtime_profile": profile.runtime, "output_schema_ambiguity": task_id == DEFAULT_TASK_ID},
            source={"index": str(package.index_path), "package_identity": package.identity(),
                    "repository": "https://github.com/QuantaAlpha/SkillGenBench",
                    "revision": revision, "bundle": str(bundle), "docs": str(docs),
                    "bundle_sha256": hashes["bundle"], "docs_sha256": hashes["docs"]},
        )
    return list(tasks.values())


def prepare_task(task: Task, destination: Path, condition: str) -> PreparedTask:
    """生成独立 BenchFlow 任务包；镜像构建上下文不包含评分脚本或参考答案。"""
    if condition != "no-skill":
        raise ValueError("当前预跑仅支持 no-skill 工程条件")
    _check_sources(task)
    destination = Path(destination).resolve()
    destination.mkdir(parents=True)
    bundle = Path(task.source["bundle"])
    source_config = task.metadata["upstream"]
    input_dir = resource_path(bundle, source_config["context"]["input_dir"])
    shutil.copytree(input_dir, destination / "context" / "input")
    shutil.copytree(Path(task.source["docs"]), destination / "context" / "docs")
    # 评分资料只存在宿主的独立副本中，不进入镜像构建上下文或作答输入。
    grading_dir = destination / "grading"
    shutil.copytree(resource_path(bundle, source_config["validation"]["tests_dir"]), grading_dir / "tests")
    shutil.copytree(resource_path(bundle, source_config["context"]["groundtruth_dir"]),
                    grading_dir / "groundtruth")
    # Windows 检出源码后再由 Linux 上传时，BenchFlow 不会替我们转换 CRLF。
    for script in (grading_dir / "tests").rglob("*.sh"):
        script.write_bytes(script.read_bytes().replace(b"\r\n", b"\n"))

    import yaml
    from environment.tasks import prepare_docker_runtime

    config = {
        "metadata": {"benchmark": "SkillGenBench", "task_id": task.id,
                     "runtime_profile": task.metadata["runtime_profile"]},
        "agent": {"timeout_sec": task.agent_timeout_sec},
        "sandbox": {"workdir": "/workspace", "build_timeout_sec": 1800},
        "verifier": {"timeout_sec": 120},
    }
    (destination / "task.md").write_text(
        "---\n" + yaml.safe_dump(config, allow_unicode=True, sort_keys=False)
        + "---\n\n" + task.instruction + "\n", encoding="utf-8", newline="\n",
    )
    environment_dir = destination / "environment"
    environment_dir.mkdir()
    # 使用 Python 3.10 和各题所需的精简依赖。上游 light 镜像包含更多软件。
    install = ["python", "-m", "pip", "install", "--no-cache-dir",
               "--index-url", "https://pypi.org/simple", *TASK_PROFILES[task.id].packages]
    (environment_dir / "Dockerfile").write_text(
        'FROM python:3.10-slim\nWORKDIR /workspace\n'
        f'RUN {json.dumps(install)}\n'
        'CMD ["sleep", "infinity"]\n', encoding="utf-8", newline="\n",
    )
    # 本机已验证官方 PyPI 可用；避免把无法连接的 TUNA 源写入任务运行环境。
    prepare_docker_runtime(destination, package_mirrors=False)
    verifier_dir = destination / "verifier"
    verifier_dir.mkdir()
    (verifier_dir / "test.sh").write_text(
        "#!/bin/bash\nset -euo pipefail\ncd /workspace\nexec bash /workspace/tests/test.sh\n",
        encoding="utf-8", newline="\n",
    )
    return PreparedTask(task_dir=destination)


def create_environment(task_dir: Path, *, output_dir: Path, **options):
    """环境的启动、执行与清理由现有调度器和 DockerEnvironment 管理。"""
    from environment import DockerEnvironment

    return DockerEnvironment(task_dir, output_dir=output_dir, workdir="/workspace",
                             cleanup_volumes=True, **options)


async def setup_environment(context: TrialContext) -> None:
    """只提供输入和公开文档，并核对任务解释器与评分资料隔离。"""
    if context.condition != "no-skill" or context.prepared.skill_catalog:
        raise ValueError("当前预跑不能注入 Skill")
    environment = context.environment
    initialized = await environment.execute([
        "mkdir", "-p", "/workspace/input", "/workspace/docs", "/workspace/output", "/workspace/skill",
    ])
    if not initialized.success:
        raise RuntimeError(f"准备作答目录失败：{initialized.stdout} {initialized.stderr}")
    for name in ("input", "docs"):
        await environment.upload(context.prepared.task_dir / "context" / name, f"/workspace/{name}")
    probe = await environment.execute([
        "python", "-c",
        f"import pathlib; {TASK_PROFILES[context.task.id].imports}; "
        "assert any(p.is_file() for p in pathlib.Path('/workspace/input').rglob('*')); "
        "assert all(not pathlib.Path(p).exists() for p in "
        "['/tests', '/workspace/tests', '/workspace/data/groundtruth']); print('task environment ready')",
    ])
    if not probe.success:
        raise RuntimeError(f"任务环境检查失败：{probe.stdout} {probe.stderr}")


async def evaluate(context: TrialContext, agent: AgentResult) -> Score:
    """作答完成后才上传原生评分资料，保留原始诊断并区分缺失评分与合法零分。"""
    return await _evaluate_artifacts(context)


def _missing_output(comments: str) -> bool:
    return comments == "Output file does not exist" or comments.startswith("Output file not found:")


async def replay_artifact(context: TrialContext, artifacts: Path | None) -> Score:
    """只回放题目要求的文件。未传产物时验证原生评分器能识别空输出。"""
    from environment.base import EnvironmentError

    if artifacts is None:
        score = await _evaluate_artifacts(context)
        if score.reward != 0 or not _missing_output(score.metrics["native_outcome"].get("comments", "")):
            raise EnvironmentError("原生评分未通过空输出检查，详见 verifier 日志")
        return score

    filename = context.task.metadata["upstream"]["expected"]["output_file"]
    if Path(filename).name != filename:
        raise ValueError(f"题目要求的产物必须是单个文件名：{filename!r}")
    source = resource_path(artifacts, filename)
    if not source.is_file():
        raise ValueError(f"缺少原始产物：{source}")
    staged = context.output_dir / "replay-input" / filename
    staged.parent.mkdir()
    shutil.copyfile(source, staged)
    with staged.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    await context.environment.upload(staged, f"/workspace/output/{filename}")
    score = await _evaluate_artifacts(context)
    return Score(score.reward, {
        **score.metrics, "replayed_artifact": {"name": filename, "sha256": digest},
    })


async def _evaluate_artifacts(context: TrialContext) -> Score:
    from environment import DockerEnvironment
    from environment.base import EnvironmentError

    if not isinstance(context.environment, DockerEnvironment):
        raise TypeError("SkillGenBench 原生预跑评分需要 DockerEnvironment")
    _check_sources(context.task)
    environment = context.environment
    await environment.download("/workspace/output", context.output_dir / "artifacts", directory=True)
    grading_dir = context.prepared.task_dir / "grading"
    await environment.upload(grading_dir / "tests", "/workspace/tests")
    created = await environment.execute(["mkdir", "-p", "/workspace/data"])
    if not created.success:
        raise EnvironmentError(f"准备评分目录失败：{created.stdout} {created.stderr}")
    await environment.upload(grading_dir / "groundtruth", "/workspace/data/groundtruth")
    rewards = await environment.verify()
    result_file = context.output_dir / "verifier" / "benchmark_result.jsonl"
    lines = [line for line in result_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        raise EnvironmentError("原生评分器没有产生诊断记录，不能将其视为零分")
    outcome = json.loads(lines[-1])
    if type(outcome.get("Process")) is not bool or type(outcome.get("Result")) is not bool:
        raise EnvironmentError("原生评分诊断缺少布尔 Process/Result 字段")
    comments = outcome.get("comments", "")
    if not isinstance(comments, str):
        raise EnvironmentError("原生评分诊断的 comments 不是字符串")
    output_error = _missing_output(comments) or comments.startswith("Failed to open output PDF:")
    reference_error = comments.startswith((
        "Reference file not found:", "Failed to parse JSON reference comparison:",
        "Groundtruth file does not exist", "Failed to open groundtruth PDF:",
        "Groundtruth has unexpected page count:",
    )) or "Failed to compare with groundtruth:" in comments
    if (not outcome["Process"] and not output_error) or reference_error:
        raise EnvironmentError(f"原生评分未能有效完成：{comments}")
    if "reward" not in rewards:
        raise EnvironmentError("原生评分缺少 reward")
    expected_reward = float(outcome["Process"] and outcome["Result"])
    if rewards["reward"] != expected_reward:
        raise EnvironmentError("reward 与原生诊断结果不一致")
    return Score(reward=rewards["reward"], metrics={
        "native_outcome": outcome, "native_rewards": rewards,
        "runtime_profile": context.task.metadata["runtime_profile"],
        "output_schema_ambiguity": context.task.metadata["output_schema_ambiguity"],
    })
