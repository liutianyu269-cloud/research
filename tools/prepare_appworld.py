"""从官方本地 AppWorld 数据目录整理开发集资源包，不下载、不调用模型。"""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory

from datasets.appworld import TASK_FORMAT, load_tasks, resource_hashes
from datasets.package import resource_path
from environment.appworld import APPWORLD_DATA_VERSION, APPWORLD_VERSION


def build_package(source: Path, destination: Path, task_ids: list[str]) -> Path:
    source = source.resolve(strict=True)
    destination = destination.resolve()
    if destination.exists():
        raise FileExistsError(f"资源包已存在，未覆盖：{destination}")
    if source == destination or source in destination.parents or destination in source.parents:
        raise ValueError("来源目录与资源包不能相互包含")
    native_data = resource_path(source, "data")
    version_file = resource_path(native_data, "version.txt")
    if version_file.read_text(encoding="utf-8").strip() != APPWORLD_DATA_VERSION:
        raise ValueError(f"需要官方数据版本 {APPWORLD_DATA_VERSION}")
    dev_file = resource_path(native_data, "datasets/dev.txt")
    dev_ids = set(dev_file.read_text(encoding="utf-8").split())
    if not task_ids or len(set(task_ids)) != len(task_ids) or set(task_ids) - dev_ids:
        raise ValueError("请提供不重复的官方开发集任务 ID")
    selected = [(task_id, resource_path(native_data, f"tasks/{task_id}")) for task_id in task_ids]
    for task_id, task_dir in selected:
        for name in ("specs.json", "dbs", "ground_truth"):
            resource_path(task_dir, name)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".appworld-package-", dir=destination.parent) as temporary:
        package = Path(temporary) / "package"
        shared = package / "shared"
        shared.mkdir(parents=True)
        for name in ("api_docs", "base_dbs"):
            original = resource_path(native_data, name)
            resource_hashes(original)  # 在复制前拒绝链接或越界资源。
            shutil.copytree(original, shared / name)
        (shared / "datasets").mkdir()
        shutil.copy2(dev_file, shared / "datasets" / "dev.txt")
        shutil.copy2(version_file, shared / "version.txt")
        for name in ("LICENSE", "README_BEFORE_SHARING.md"):
            if (native_data / name).is_file():
                shutil.copy2(resource_path(native_data, name), shared / name)
        rows = []
        versions = set()
        for task_id, original in selected:
            hashes = resource_hashes(original)
            relative = f"tasks/{task_id}"
            shutil.copytree(original, package / relative)
            if hashes != resource_hashes(package / relative) or hashes != resource_hashes(original):
                raise ValueError(f"复制时任务发生变化：{task_id}")
            specs = json.loads((original / "specs.json").read_text(encoding="utf-8"))
            versions.add(specs["db_version"])
            rows.append({"id": task_id, "task": relative, "task_sha256": hashes})
        if versions != {APPWORLD_DATA_VERSION}:
            raise ValueError(f"当前AppWorld运行时需要数据版本 {APPWORLD_DATA_VERSION}")
        metadata = {
            "schema_version": 1, "id": "appworld", "task_format": TASK_FORMAT,
            "version": f"{APPWORLD_VERSION}-data-{next(iter(versions))}-dev-r1",
            "provenance": {"repository": "https://github.com/StonyBrookNLP/appworld",
                           "package_version": APPWORLD_VERSION, "split": "dev",
                           "data_bundle_url": "https://s3.us-west-2.amazonaws.com/appworld.dev/data-0.1.0.bundle"},
        }
        bundle = source / "data.bundle"
        if bundle.is_file():
            metadata["provenance"]["downloaded_bundle_sha256"] = hashlib.sha256(bundle.read_bytes()).hexdigest()
        index = {"schema_version": 1, "task_count": len(rows), "shared": "shared",
                 "shared_sha256": resource_hashes(shared), "tasks": rows}
        for name, document in (("dataset.json", metadata), ("index.json", index)):
            (package / name).write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        load_tasks(package / "index.json", task_ids)
        package.rename(destination)
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="包含官方 data/ 的本地 AppWorld 根目录")
    parser.add_argument("--destination", type=Path, required=True, help="尚不存在的资源包目录")
    parser.add_argument("--task-ids", nargs="+", required=True, help="显式选择的官方 dev 任务 ID")
    options = parser.parse_args()
    print(build_package(options.source, options.destination, options.task_ids))


if __name__ == "__main__":
    main()
