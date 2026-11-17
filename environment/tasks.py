"""根据现有拆分的 research 索引重建原生任务包。"""

import json
from pathlib import Path
import re
import shutil

from datasets.package import read_package_index, resource_path

from .runtime import (CONTAINER_RUNTIME_PROBE, WORKER_PYTHON_EXECUTABLE,
                      WORKER_RUNTIME_DIRECTORY, WORKER_RUNTIME_IMAGE,
                      worker_runtime_build_command)


_PIP_MIRROR_MARKER = "# research: pip mirror (TUNA)"
_PIP_INDEX_URL = "https://pypi.tuna.tsinghua.edu.cn/simple"
_APT_MIRROR_MARKER = "# research: APT mirror (TUNA)"
_APT_MIRROR_COMMAND = r"""
if [ ! -f /etc/os-release ]; then
    echo 'research：已跳过 APT 镜像源配置（缺少 /etc/os-release）'
    exit 0
fi
. /etc/os-release
case "$ID" in
    ubuntu|debian) ;;
    *) echo "research：已跳过 APT 镜像源配置（$ID）"; exit 0 ;;
esac
if [ "$(id -u)" -ne 0 ]; then
    echo 'research：配置 APT 镜像源需要在首个 RUN 前取得 root 权限' >&2
    exit 1
fi
# HTTP 也适用于未安装 ca-certificates 的最小镜像；APT 签名校验保持启用。
for source in /etc/apt/sources.list /etc/apt/sources.list.d/*.list /etc/apt/sources.list.d/*.sources; do
    [ -f "$source" ] || continue
    sed -E -i \
        -e 's@https?://([[:alnum:]-]+\.)?(archive|security)\.ubuntu\.com/ubuntu(/|[[:space:]]|$)@http://mirrors.tuna.tsinghua.edu.cn/ubuntu\3@g' \
        -e 's@https?://ports\.ubuntu\.com/ubuntu-ports(/|[[:space:]]|$)@http://mirrors.tuna.tsinghua.edu.cn/ubuntu-ports\1@g' \
        -e 's@https?://(deb|security)\.debian\.org/debian-security(/|[[:space:]]|$)@http://mirrors.tuna.tsinghua.edu.cn/debian-security\2@g' \
        -e 's@https?://security\.debian\.org/debian(/|[[:space:]]|$)@http://mirrors.tuna.tsinghua.edu.cn/debian-security\1@g' \
        -e 's@https?://(deb\.debian\.org|ftp\.([[:alnum:]-]+\.)?debian\.org)/debian(/|[[:space:]]|$)@http://mirrors.tuna.tsinghua.edu.cn/debian\3@g' \
        "$source"
done
echo "research：已为 $ID 配置 APT 清华镜像源（TUNA）"
""".strip()


def _dockerfile_instructions(lines: list[str], dockerfile: Path):
    """读取完整指令的行号与参数，跳过续行和 heredoc 中的数据。"""
    escape = "\\"
    i = 0
    while i < len(lines):
        start = i
        line = lines[i]
        i += 1
        if not line.strip() or line.lstrip().startswith("#"):
            directive = re.fullmatch(r"\s*#\s*escape\s*=\s*([\\`])\s*", line)
            if directive:
                escape = directive[1]
            continue
        # 每次读取完整指令，避免将续行误判为新指令。
        while line.rstrip("\r\n").endswith(escape) and i < len(lines):
            line = lines[i]
            i += 1
            while line.lstrip().startswith("#") and i < len(lines):
                line = lines[i]
                i += 1
        instruction = re.match(r"\s*([a-z]+)\s+(.*)", lines[start], re.IGNORECASE)
        if instruction is None:
            continue
        keyword = instruction[1].upper()
        end = i
        arguments = "".join(lines[start:end]).replace(escape + "\n", " ").split()[1:]
        # heredoc 中可能包含作为数据的 FROM/RUN，也可能嵌入 Python 导入代码。
        if keyword in {"RUN", "COPY"}:
            command = "".join(lines[start:i])
            for heredoc in re.finditer(r"<<(-?)[ \t]*(?:'([^']+)'|\"([^\"]+)\"|([a-zA-Z_][a-zA-Z0-9_]*))", command):
                delimiter = next(value for value in heredoc.groups()[1:] if value is not None)
                while i < len(lines):
                    body = lines[i].rstrip("\r\n")
                    i += 1
                    if (body.lstrip("\t") if heredoc[1] else body) == delimiter:
                        break
                else:
                    raise ValueError(f"Dockerfile 的 heredoc 未闭合：{delimiter!r}: {dockerfile}")
        yield start, end, keyword, arguments


def _inject_package_mirrors(dockerfile: Path) -> None:
    """在 FROM 后设置 pip，并在每个阶段的首个 RUN 前准备 APT。"""
    text = dockerfile.read_text(encoding="utf-8-sig")
    inject_pip = _PIP_MIRROR_MARKER not in text
    inject_apt = _APT_MIRROR_MARKER not in text
    if not inject_pip and not inject_apt:
        return
    lines = text.splitlines(keepends=True)
    pip_block = f"\n{_PIP_MIRROR_MARKER}\nENV PIP_INDEX_URL={_PIP_INDEX_URL}\n"
    apt_block = f"\n{_APT_MIRROR_MARKER}\nRUN " + json.dumps(
        ["/bin/sh", "-ec", _APT_MIRROR_COMMAND],
    ) + "\n"
    insertions = {}
    pending_stage = False
    for start, end, keyword, arguments in _dockerfile_instructions(lines, dockerfile):
        if keyword == "FROM":
            image = next(part for part in arguments if not part.startswith("--"))
            pending_stage = image.lower() != "scratch" and inject_apt
            if image.lower() != "scratch" and inject_pip:
                insertions[end] = pip_block
        elif keyword == "RUN" and pending_stage:
            insertions[start] = insertions.get(start, "") + apt_block
            pending_stage = False
    # 没有 RUN 的最终阶段也可能在后续添加桌面安装命令。
    if pending_stage:
        insertions[len(lines)] = insertions.get(len(lines), "") + apt_block
    if insertions:
        rewritten = "".join(insertions.get(index, "") + line
                            for index, line in enumerate(lines))
        rewritten += insertions.get(len(lines), "")
        dockerfile.write_text(rewritten, encoding="utf-8", newline="\n")


def _native_task_text(source: Path) -> str:
    """重命名 YAML 中旧版沙箱配置键，保留 Markdown 正文。"""
    import yaml

    text = source.read_text(encoding="utf-8-sig")
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return text
    end = next((i for i, line in enumerate(lines[1:], 1)
                if line.strip() == "---"), None)
    if end is None:
        raise ValueError(f"任务的 YAML 前置元数据未闭合：{source}")
    config = yaml.safe_load("".join(lines[1:end]))
    if not isinstance(config, dict):
        raise ValueError(f"任务的 YAML 前置元数据必须为映射：{source}")
    if "environment" not in config:
        return text
    if "sandbox" in config:
        raise ValueError(f"任务同时声明了 environment 和 sandbox：{source}")
    config["sandbox"] = config.pop("environment")
    header = yaml.safe_dump(config, allow_unicode=True, sort_keys=False)
    return "---\n" + header + "---\n" + "".join(lines[end + 1:])


def _inject_worker_runtime(dockerfile: Path) -> None:
    """单独构建 Python，只将独立目录复制到主镜像最终阶段。"""
    marker = "# research: isolated worker runtime"
    stage = "research-worker-runtime"
    text = dockerfile.read_text(encoding="utf-8-sig")
    if marker in text:
        return
    if "# research: worker runtime" in text:
        raise ValueError("任务副本包含旧版系统依赖安装步骤，请从原始数据重新生成")
    lines = text.splitlines(keepends=True)
    stages = [instruction for instruction in _dockerfile_instructions(lines, dockerfile)
              if instruction[2] == "FROM"]
    if not stages:
        raise ValueError(f"Dockerfile 缺少 FROM：{dockerfile}")
    for _, _, _, arguments in stages:
        if len(arguments) >= 3 and arguments[-2].upper() == "AS" and arguments[-1].lower() == stage:
            raise ValueError(f"Dockerfile 使用了框架保留的阶段名称 {stage}：{dockerfile}")
    final_start, _, _, final_arguments = stages[-1]
    # 放在最终 FROM 前，保留原有前置阶段的编号和最终阶段的用户、目录、环境。
    platform = " ".join(argument for argument in final_arguments if argument.startswith("--platform="))
    runtime_stage = (
        f"\n{marker}\nFROM {platform + ' ' if platform else ''}{WORKER_RUNTIME_IMAGE} AS {stage}\n"
        "RUN " + json.dumps(["/bin/sh", "-ec", worker_runtime_build_command()]) + "\n\n"
    )
    directory = WORKER_RUNTIME_DIRECTORY
    collision_check = (
        f"if [ -e {directory} ] || [ -L {directory} ]; then "
        f"echo 'research: reserved runtime directory already exists: {directory}' >&2; exit 1; fi"
    )
    suffix = (
        f"\n\n{marker}\n"
        "RUN " + json.dumps(["/bin/sh", "-ec", collision_check]) + "\n"
        f"COPY --from={stage} {directory} {directory}\n"
        "RUN " + json.dumps([
            WORKER_PYTHON_EXECUTABLE, "-I", "-B", "-c", CONTAINER_RUNTIME_PROBE,
        ]) + "\n"
    )
    rewritten = "".join(lines[:final_start]) + runtime_stage + "".join(lines[final_start:]) + suffix
    dockerfile.write_text(rewritten, encoding="utf-8", newline="\n")


def prepare_docker_runtime(task_dir: str | Path, *, package_mirrors: bool = True) -> None:
    """为任务副本准备独立 Python；原有任务默认继续配置已有镜像源。"""
    environment_dir = Path(task_dir) / "environment"
    if package_mirrors:
        for dockerfile in sorted(environment_dir.rglob("Dockerfile*")):
            if dockerfile.is_file():
                _inject_package_mirrors(dockerfile)
    main_dockerfile = environment_dir / "Dockerfile"
    if main_dockerfile.is_file():
        _inject_worker_runtime(main_dockerfile)


def materialize_skillsbench_task(index_path: str | Path, task_id: str,
                                destination: str | Path) -> Path:
    """将任务数据复制到新的持久准备目录，不修改原始数据。

    准备目录由调用方管理；此处不启动环境。
    索引必须来自标准资源包，所有资源路径相对包根目录解析。
    仅在副本 task.md 中将 environment 改名为 sandbox，以适配 BenchFlow 0.7.8。
    副本中的 Dockerfile* 将 pip 和官方 Ubuntu/Debian APT 源切换为清华镜像。
    主 Dockerfile 通过独立构建阶段复制框架 Python，不安装或升级任务系统包。
    """
    package = read_package_index(index_path, task_format="research-skillsbench-v1")
    rows = package.index["tasks"]
    matches = [row for row in rows if row["id"] == task_id]
    if len(matches) != 1:
        raise ValueError(f"应有一个名称为 {task_id!r} 的任务，实际找到 {len(matches)}")
    row = matches[0]
    destination = Path(destination).resolve()
    if destination.exists():
        raise FileExistsError(f"准备目录已存在：{destination}")
    entries = [(row["task_file"], "task.md"),
               (row["environment_dir"], "environment"),
               (row["verifiler_dir"], "verifier"),
               (row["oracle_dir"], "oracle")]
    entries.extend((path, Path(path).name) for path in row.get("extra_paths", []))
    names = set()
    checked = []
    for path, name in entries:
        if name.casefold() in names or name in {"", ".", ".."}:
            raise ValueError(f"准备路径冲突：{name}")
        names.add(name.casefold())
        source = resource_path(package.root, path)
        if name in {"environment", "verifier", "oracle"} and not source.is_dir():
            raise ValueError(f"任务资源必须为目录：{source}")
        if source == destination or source in destination.parents or destination in source.parents:
            raise ValueError("准备目录与任务源目录重叠")
        if source.is_dir():
            for item in source.rglob("*"):
                if item.is_symlink() or item.is_junction():
                    raise ValueError(f"不支持链接形式的任务资源：{item}")
        checked.append((source, name))
    task_text = _native_task_text(checked[0][0])
    destination.mkdir(parents=True)
    for source, name in checked:
        target = destination / name
        if name == "task.md":
            target.write_text(task_text, encoding="utf-8")
        elif source.is_dir():
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)
    prepare_docker_runtime(destination)
    return destination
