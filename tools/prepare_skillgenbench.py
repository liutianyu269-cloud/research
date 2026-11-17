"""从固定的上游 checkout 生成单题资源包，不下载、不调用模型、不覆盖已有目录。"""

import argparse
import json
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory

from datasets.package import resource_path
from datasets.skillgenbench import TASK_FORMAT, UPSTREAM_REVISION, _snapshot, load_tasks


def build_package(source: Path, destination: Path) -> Path:
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
    sources = {
        "bundle": "skill_evaluation/code_repo/pypdf2/PyPDF2_gtb03",
        "docs": "data_source/code_repo/pypdf2/shared/materials/docs",
    }
    directories = {key: resource_path(source, value) for key, value in sources.items()}
    hashes = {key: _snapshot(directory) for key, directory in directories.items()}
    destination.parent.mkdir(parents=True, exist_ok=True)
    # 同一父目录构建成功后再改名；出错仅清理脚本自己创建的临时目录。
    with TemporaryDirectory(prefix=".skillgenbench-package-", dir=destination.parent) as temporary:
        package = Path(temporary) / "package"
        package.mkdir()
        row = {"id": "PyPDF2_gtb03", "bundle": "tasks/PyPDF2_gtb03", "docs": "shared/pypdf2/docs"}
        for key, directory in directories.items():
            shutil.copytree(directory, package / row[key])
            if _snapshot(directory) != hashes[key] or _snapshot(package / row[key]) != hashes[key]:
                raise ValueError(f"打包过程中 {key} 来源或副本发生了变化")
            row[f"{key}_sha256"] = hashes[key]
        metadata = {
            "schema_version": 1, "id": "skillgenbench", "version": "5a8bd61d81-pypdf-pilot-r1",
            "task_format": TASK_FORMAT,
            "provenance": {"repository": "https://github.com/QuantaAlpha/SkillGenBench",
                           "revision": revision, "source_paths": sources,
                           "runtime_profile": "pypdf-minimal",
                           "scope": "PyPDF2_gtb03 only; no-skill engineering pilot"},
        }
        for name, document in (("dataset.json", metadata),
                               ("index.json", {"schema_version": 1, "task_count": 1, "tasks": [row]})):
            (package / name).write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n",
                                        encoding="utf-8", newline="\n")
        # 如上游提供许可证，连同来源一起保留；不凭空宣称数据的许可。
        for name in ("LICENSE", "LICENSE.md", "LICENSE.txt", "NOTICE"):
            if (source / name).is_file():
                shutil.copy2(resource_path(source, name), package / name)
        load_tasks(package / "index.json", [row["id"]])
        package.rename(destination)
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="固定提交的 SkillGenBench checkout")
    parser.add_argument("--destination", type=Path, required=True, help="尚不存在的资源包目录")
    options = parser.parse_args()
    print(build_package(options.source, options.destination))


if __name__ == "__main__":
    main()
