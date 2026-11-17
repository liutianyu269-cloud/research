"""每个 trial 独占官方 AppWorld 服务，由 Docker 管理持续会话生命周期。"""

import asyncio
import json
from pathlib import Path
import shlex
import time

from environment.base import EnvironmentError
from environment.docker import DockerEnvironment


APPWORLD_VERSION = "0.1.3.post1"
APPWORLD_DATA_VERSION = "0.1.0"
APPWORLD_ROOT = "/opt/appworld"
APPWORLD_EXPERIMENT = "research"

# 只在容器内访问官方服务，不开放宿主端口；JSON 参数始终作为数据传递。
_CLIENT = r'''
import json
import sys
import urllib.request

operation, payload, timeout = sys.argv[1], json.loads(sys.argv[2]), float(sys.argv[3])
if operation not in {"health", "initialize", "execute", "evaluate", "save_logs", "close"}:
    raise ValueError("Unsupported AppWorld operation")
request = urllib.request.Request(
    "http://127.0.0.1:9000/" + ("" if operation == "health" else operation),
    data=None if operation == "health" else json.dumps(payload).encode(),
    headers={"Content-Type": "application/json"},
)
with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(request, timeout=timeout) as response:
    result = json.load(response)
if operation == "execute":
    output = result["output"]
    if not isinstance(output, str):
        raise TypeError("AppWorld execute must return text")
    print(output)
    if output.startswith("Execution failed."):
        raise SystemExit(1)
else:
    print(json.dumps(result))
'''


class AppWorldEnvironment(DockerEnvironment):
    def __init__(self, task_dir, *, output_dir, **options):
        session = json.loads((Path(task_dir) / "appworld-session.json").read_text(encoding="utf-8"))
        self.task_id = session["task_id"]
        self.instruction = session["instruction"]
        self._initialized = False
        super().__init__(task_dir, output_dir=output_dir, workdir=APPWORLD_ROOT,
                         cleanup_volumes=True, **options)

    @property
    def native_output_path(self) -> str:
        return f"{APPWORLD_ROOT}/experiments/outputs/{APPWORLD_EXPERIMENT}/tasks/{self.task_id}"

    def _command(self, operation: str, payload: dict, timeout: float) -> list[str]:
        return [self.worker_python_executable, "-I", "-B", "-c", _CLIENT,
                operation, json.dumps(payload), str(max(1, timeout - 2))]

    async def _request(self, operation: str, payload: dict, *, timeout: float = 60) -> dict:
        result = await self.execute(self._command(operation, payload, timeout), timeout=timeout)
        if not result.success:
            raise EnvironmentError(f"AppWorld {operation} 失败：{result.stdout} {result.stderr}")
        response = json.loads(result.stdout)
        if not isinstance(response, dict):
            raise EnvironmentError(f"AppWorld {operation} 未返回 JSON 对象")
        return response

    async def execute(self, argv, *, cwd=None, timeout=60, service="main"):
        result = await super().execute(argv, cwd=cwd, timeout=timeout, service=service)
        if result.timed_out:
            # 杀掉HTTP客户端不能证明服务端的代码已停；销毁本trial防止后续操作状态不明。
            await super().destroy()
            raise EnvironmentError("AppWorld命令超时且会话状态不确定，已销毁本trial容器，不能继续作答或记为有效评分")
        return result

    async def start(self) -> None:
        await super().start()
        deadline = time.monotonic() + self.ready_timeout
        try:
            while True:
                result = await self.execute(self._command("health", {}, 5), timeout=5)
                if result.success:
                    break
                if time.monotonic() >= deadline:
                    raise EnvironmentError(f"AppWorld 服务未就绪：{result.stderr}")
                await asyncio.sleep(0.25)
        except BaseException as exc:
            try:
                await self.destroy()
            except BaseException as cleanup_error:
                exc.add_note(f"清理失败：{cleanup_error}")
            raise

    async def initialize_task(self) -> dict:
        if self._initialized:
            raise EnvironmentError("同一 trial 不允许重复初始化并重置 AppWorld 状态")
        response = await self._request("initialize", {
            "task_id": self.task_id, "experiment_name": APPWORLD_EXPERIMENT,
            "timeout_seconds": 20,
        })
        self._initialized = True
        task = response["output"]
        if task["task_id"] != self.task_id or task["instruction"] != self.instruction:
            raise EnvironmentError("AppWorld 实际任务与资源包记录不一致")
        return task

    def code_command(self, code: str, *, timeout: float) -> str:
        if not self._initialized:
            raise EnvironmentError("AppWorld 会话尚未初始化")
        return shlex.join(self._command("execute", {"task_id": self.task_id, "code": code}, timeout))

    async def evaluate_task(self) -> dict:
        if not self._initialized:
            raise EnvironmentError("AppWorld 会话尚未初始化")
        await self._request("save_logs", {"task_id": self.task_id})
        return (await self._request("evaluate", {
            "task_id": self.task_id, "suppress_errors": True, "report": False,
        }, timeout=120))["output"]

    async def destroy(self) -> None:
        try:
            if self.state == "running" and self._initialized:
                await self._request("close", {"task_id": self.task_id}, timeout=30)
                self._initialized = False
        finally:
            await super().destroy()


def create_environment(task_dir: Path, *, output_dir: Path, **options):
    return AppWorldEnvironment(task_dir, output_dir=output_dir, **options)
