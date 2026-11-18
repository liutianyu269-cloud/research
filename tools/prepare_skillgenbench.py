"""从固定的上游 checkout 生成资源包，不下载、不调用模型、不覆盖已有目录。"""

import argparse
import json
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory

from datasets.package import resource_path
from datasets.skillgenbench import (
    DEFAULT_TASK_ID, MATRIX_PACKAGE_VERSION, PILOT_TASK_IDS, TASK_FORMAT, TASK_PROFILES,
    UPSTREAM_REVISION, _snapshot, load_tasks,
)


def build_package(source: Path, destination: Path, task_ids: list[str] | None = None) -> Path:
    """复制已核对的原题及公开文档，记录来源和每个文件的实际 SHA256。"""
    source = source.resolve(strict=True)
    destination = destination.resolve()
    if destination.exists():
        raise FileExistsError(f"资源包目录已存在，未覆盖：{destination}")
    if source == destination or source in destination.parents or destination in source.parents:
        raise ValueError("资源包与上游来源目录不能相互包含")
    revision = subprocess.run(
        ["git", "-C", str(source), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True, timeout=10,
    ).stdout.strip()
    if revision != UPSTREAM_REVISION:
        raise ValueError(f"需要上游提交 {UPSTREAM_REVISION}，实际 {revision}")
    legacy = task_ids is None
    task_ids = [DEFAULT_TASK_ID] if legacy else task_ids
    if not task_ids or len(set(task_ids)) != len(task_ids) or set(task_ids) - TASK_PROFILES.keys():
        raise ValueError(f"请选择不重复的已支持任务：{', '.join(TASK_PROFILES)}")
    matrix = bool(set(task_ids) - PILOT_TASK_IDS)
    destination.parent.mkdir(parents=True, exist_ok=True)
    # 同一父目录构建成功后再改名；出错仅清理脚本自己创建的临时目录。
    with TemporaryDirectory(prefix=".skillgenbench-package-", dir=destination.parent) as temporary:
        package = Path(temporary) / "package"
        package.mkdir()
        rows, sources = [], {}
        for task_id in task_ids:
            repo = TASK_PROFILES[task_id].repo
            task_sources = {
                "bundle": f"skill_evaluation/code_repo/{repo}/{task_id}",
                "docs": f"data_source/code_repo/{repo}/shared/materials/docs",
            }
            row = {"id": task_id, "bundle": f"tasks/{task_id}",
                   "docs": "shared/pypdf2/docs" if legacy else f"docs/{task_id}"}
            for key, value in task_sources.items():
                directory = resource_path(source, value, must_exist=key == "bundle")
                if key == "docs" and not directory.exists():
                    if not matrix and repo != "soundfile":
                        raise FileNotFoundError(f"请先检出公开文档：{directory}")
                    task_docs = f"{task_sources['bundle']}/context/docs"
                    directory = resource_path(source, task_docs, must_exist=False)
                    if not directory.exists():
                        (package / row[key]).mkdir(parents=True)
                        row[f"{key}_sha256"] = {}
                        task_sources[key] = None
                        continue
                    task_sources[key] = task_docs
                hashes = _snapshot(directory)
                shutil.copytree(directory, package / row[key])
                if _snapshot(directory) != hashes or _snapshot(package / row[key]) != hashes:
                    raise ValueError(f"打包过程中 {task_id} 的 {key} 来源或副本发生了变化")
                row[f"{key}_sha256"] = hashes
            rows.append(row)
            sources[task_id] = task_sources
        metadata = {
            "schema_version": 1, "id": "skillgenbench",
            "version": MATRIX_PACKAGE_VERSION if matrix else "5a8bd61d81-small-pilot-r2",
            "task_format": TASK_FORMAT,
            "provenance": {"repository": "https://github.com/QuantaAlpha/SkillGenBench",
                           "revision": revision, "source_paths": sources,
                           "scope": ("Screened code-repository task sample, no-skill condition"
                                     if matrix else "Selected no-skill engineering pilot tasks")},
        }
        if legacy:
            # 保留历史单题包的描述与索引身份，兼容既有实验复现。
            metadata["version"] = "5a8bd61d81-pypdf-pilot-r1"
            metadata["provenance"].pop("scope")
            metadata["provenance"].update(source_paths=sources[DEFAULT_TASK_ID],
                                          runtime_profile="pypdf-minimal",
                                          scope="PyPDF2_gtb03 only; no-skill engineering pilot")
        for name, document in (("dataset.json", metadata),
                               ("index.json", {"schema_version": 1, "task_count": len(rows), "tasks": rows})):
            (package / name).write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n",
                                        encoding="utf-8", newline="\n")
        # 如上游提供许可证，连同来源一起保留；不凭空宣称数据的许可。
        for name in ("LICENSE", "LICENSE.md", "LICENSE.txt", "NOTICE"):
            if (source / name).is_file():
                shutil.copy2(resource_path(source, name), package / name)
        load_tasks(package / "index.json", task_ids)
        package.rename(destination)
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="固定提交的 SkillGenBench checkout")
    parser.add_argument("--destination", type=Path, required=True, help="尚不存在的资源包目录")
    parser.add_argument("--task-ids", nargs="+", help="显式选择已支持任务，默认只打包原预跑题")
    options = parser.parse_args()
    print(build_package(options.source, options.destination, options.task_ids))


if __name__ == "__main__":
    main()
