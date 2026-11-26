"""Run one historical-baseline comparison with a hard upstream request limit."""

import argparse
from contextlib import nullcontext
import fcntl
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
from secrets import token_urlsafe
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Lock, Thread
import tomllib
from urllib.error import HTTPError, URLError
from urllib.request import build_opener, HTTPRedirectHandler, ProxyHandler, Request
from uuid import uuid4

from dotenv import dotenv_values


HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[1]
THINGO_URL = "https://uniapi.thingo.com.cn/v1"
COMPLETIONS = "/v1/chat/completions"
REQUEST_LIMIT = 6
RESULTS = WORKSPACE / "outputs" / "skill-lab-v2" / "thingo"


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, url):
        return None


class RequestLedger:
    def __init__(self, path):
        self.path = path
        self.lock = Lock()
        rows = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
        self.used = sum(json.loads(row)["event"] == "forwarded" for row in rows)
        self.blocked = 0

    def reserve(self, attempt, size):
        with self.lock, self.path.open("a", encoding="utf-8") as log:
            if self.used >= REQUEST_LIMIT:
                self.blocked += 1
                log.write(json.dumps({"event": "blocked", "attempt": attempt}) + "\n")
                return False
            self.used += 1
            log.write(json.dumps({"event": "forwarded", "attempt": attempt,
                                  "request": self.used, "bytes": size}) + "\n")
            log.flush()
            os.fsync(log.fileno())
            return True


def proxy_handler(gateway, key, local_token, ledger, attempt):
    opener = build_opener(ProxyHandler({}), NoRedirects())

    class GatewayHandler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            return

        def reply(self, status, payload):
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_POST(self):
            if self.path != COMPLETIONS:
                self.reply(404, b'{"error":{"message":"Unexpected pilot endpoint"}}')
                return
            if not hmac.compare_digest(self.headers.get("Authorization", ""), f"Bearer {local_token}"):
                self.reply(403, b'{"error":{"message":"Invalid local pilot token"}}')
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = 0
            if not 0 < length <= 2 * 1024 * 1024:
                self.reply(413, b'{"error":{"message":"Unexpected pilot request size"}}')
                return
            body = self.rfile.read(length)
            if len(body) != length or not ledger.reserve(attempt, length):
                self.reply(403, b'{"error":{"message":"The Thingo request limit has been reached"}}')
                return
            upstream = Request(gateway + "/chat/completions", data=body, method="POST", headers={
                "Authorization": f"Bearer {key}", "Content-Type": "application/json",
                "Accept": self.headers.get("Accept", "application/json"), "Accept-Encoding": "identity",
            })
            try:
                response = opener.open(upstream, timeout=80)
            except HTTPError as error:
                with error:
                    payload = error.read(64 * 1024).replace(key.encode(), b"<redacted>")
                self.reply(error.code, payload)
                return
            except (URLError, TimeoutError):
                self.reply(502, b'{"error":{"message":"Could not reach the Thingo gateway"}}')
                return
            with response:
                self.send_response(response.status)
                self.send_header("Content-Type", response.headers.get("Content-Type", "application/json"))
                self.send_header("Connection", "close")
                self.end_headers()
                self.close_connection = True
                try:
                    while chunk := response.read1(64 * 1024):
                        self.wfile.write(chunk)
                except (ConnectionError, TimeoutError):
                    pass

    return GatewayHandler


def matching_baseline(project, task_id, *, allow_unscored_baseline=False):
    manifest = project / "logs/exp/skillgenbench/dsh/deepseek-flash/liutianyu-sgb-matrix-r1/manifest.json"
    baseline = read_json(manifest)["config"]
    config_path = project / "config/agents/dsh-skillgenbench-deepseek.toml"
    source = config_path.read_text(encoding="utf-8")
    config = tomllib.loads(source)
    if any(config[part] != baseline[part] for part in ("model", "agent")):
        raise ValueError("The current DSH/model configuration differs from the historical baseline")
    dataset = project / "data/skillgenbench-matrix"
    for filename in ("dataset", "index"):
        actual = hashlib.sha256((dataset / f"{filename}.json").read_bytes()).hexdigest()
        if actual != baseline["dataset"]["package_identity"][filename + "_sha256"]:
            raise ValueError(f"Historical benchmark package differs: {filename}.json")
    comparison = read_json(WORKSPACE / "outputs" / "skillgenbench-dsh-10-comparison.json")
    matches = [case for case in comparison["tasks"] if case["task_id"] == task_id]
    if len(matches) != 1:
        raise ValueError("Choose a task from the original ten-task baseline")
    if not allow_unscored_baseline and matches[0]["no_skill_mean_native_score"] is None:
        raise ValueError("Choose an original task with a usable no-Skill baseline")
    return dataset, config, source, matches[0]


def observed_skill_usage(result_file, record):
    trial_id = record.get("trial_id")
    if result_file is None or not trial_id:
        return [], []
    events = result_file.parent / "trials" / trial_id / "agent" / "tool-calls.jsonl"
    if not events.is_file():
        return [], []
    commands = {}
    reads = set()
    scripts = set()
    for line in events.read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        index = event["index"]
        if event["type"] == "call":
            commands[index] = event.get("arguments", {}).get("command", "")
        elif event["type"] == "result" and event.get("exit_code") == 0:
            if "SKILL.md" in commands.get(index, "") and "\nname:" in event.get("stdout", ""):
                reads.add(index)
            command = commands.get(index, "")
            if "python" in command and "/workspace/skill/scripts/" in command:
                scripts.add(index)
    return sorted(reads), sorted(scripts)


def run_trial(project, node_bin, task_id, skill, *, results=RESULTS,
              allow_unscored_baseline=False, short_runtime=False):
    dataset, original, original_text, baseline = matching_baseline(
        project, task_id, allow_unscored_baseline=allow_unscored_baseline,
    )
    return execute_trial(
        project, node_bin, task_id, skill, results, dataset, original, original_text,
        dataset_module="datasets.skillgenbench", adapter_module="online_adapter",
        baseline=baseline, short_runtime=short_runtime,
    )


def execute_trial(project, node_bin, task_id, skill, results, dataset, config, agent_config_text,
                  *, dataset_module, adapter_module, baseline=None, short_runtime=True):
    from online_adapter import skill_files

    condition = "with-skill" if skill is not None else "no-skill"
    files = skill_files(skill) if skill is not None else []
    subprocess.run([str(node_bin / "node"), "--version"], check=True)
    subprocess.run(["docker", "info", "--format", "{{.ServerVersion}}"], check=True)
    model = config["model"]
    if model["base_url"] != THINGO_URL:
        raise ValueError("The historical configuration points to an unfamiliar gateway")
    key_name = model["api_key_env"]
    key = os.environ.get(key_name) or dotenv_values(project / ".env").get(key_name)
    if not key:
        raise ValueError("The previous gateway key is unavailable")
    ledger = RequestLedger(results / "request-ledger.jsonl")
    if ledger.used:
        raise ValueError("The one paid comparison has already made an upstream request")
    attempt = "pilot-" + uuid4().hex[:12]
    output = results / attempt
    output.mkdir()
    write_json(output / "plan.json", {"task": task_id, "condition": condition, "budget": REQUEST_LIMIT,
        "baseline": baseline["no_skill"] if baseline is not None else None,
        "skillFiles": {path.as_posix(): hashlib.sha256((skill / path).read_bytes()).hexdigest()
                       for path in files}})
    token = token_urlsafe(32)
    handler = proxy_handler(model["base_url"], key, token, ledger, attempt)
    with ThreadingHTTPServer(("127.0.0.1", 0), handler) as proxy:
        thread = Thread(target=proxy.serve_forever, daemon=True)
        thread.start()
        base_url = f"http://127.0.0.1:{proxy.server_port}/v1"
        try:
            runtime_location = TemporaryDirectory(prefix="sgb-") if short_runtime else nullcontext(output / "runs")
            with TemporaryDirectory(prefix="liutianyu-thingo-config-") as temporary, runtime_location as runtime:
                configs = Path(temporary)
                runtime_dir = Path(runtime)
                agent_file = configs / "agent.toml"
                agent_file.write_text(agent_config_text.replace(model["base_url"], base_url, 1), encoding="utf-8")
                dataset_file = configs / "dataset.toml"
                dataset_file.write_text(
                    f"[dataset]\npackage = {json.dumps(str(dataset))}\n"
                    f'loader = "{dataset_module}:load_tasks"\n'
                    f'prepare = "{adapter_module}:prepare_task"\n'
                    f'setup = "{adapter_module}:setup_environment"\n', encoding="utf-8")
                eval_file = configs / "evaluation.toml"
                eval_file.write_text(
                    f"output_dir = {json.dumps(str(runtime_dir))}\n"
                    f'conditions = ["{condition}"]\nrepeats = 1\npass_threshold = 1.0\n'
                    f'[evaluator]\nfunction = "{dataset_module}:evaluate"\n', encoding="utf-8")
                no_proxy = ",".join(filter(None, (os.environ.get("NO_PROXY"), "127.0.0.1", "localhost")))
                environment = dict(os.environ, **{key_name: token, "LTY_PILOT_SKILL": str(skill),
                    "PYTHONPATH": os.pathsep.join((str(project), str(HERE))),
                    "PATH": os.pathsep.join((str(node_bin), os.environ["PATH"])),
                    "TIKTOKEN_CACHE_DIR": str(project / "logs/tiktoken-cache"),
                    "NO_PROXY": no_proxy, "no_proxy": no_proxy})
                command = [sys.executable, "-B", "-X", "utf8", "-u", "-m", "evaluation",
                           "--name", attempt, "--dataset", str(dataset_file), "--agent", str(agent_file),
                           "--environment", str(project / "config/environments/skillgenbench.toml"),
                           "--evaluation", str(eval_file), "--task", task_id]
                with (output / "experiment.log").open("w", encoding="utf-8") as log:
                    try:
                        process = subprocess.run(command, cwd="/tmp", env=environment, stdout=log,
                                                 stderr=subprocess.STDOUT)
                    finally:
                        if short_runtime:
                            shutil.copytree(runtime_dir, output / "runs")
        finally:
            proxy.shutdown()
            thread.join()
    result_files = list((output / "runs").rglob("results.jsonl"))
    result_file = result_files[0] if len(result_files) == 1 else None
    rows = [json.loads(line) for line in result_file.read_text(encoding="utf-8").splitlines()
            if line.strip()] if result_file is not None else []
    record = rows[0] if len(rows) == 1 else {}
    score = record.get("reward")
    base = baseline["no_skill_mean_native_score"] if baseline is not None else None
    native = (record.get("metrics") or {}).get("native_outcome") or {}
    agent = record.get("agent") or {}
    reads, scripts = observed_skill_usage(result_file, record)
    evidence = {"task": task_id, "condition": condition, "harness": "dsh",
                "model": model["model"], "gateway": "Thingo",
                "attempt": attempt, "requestLimit": REQUEST_LIMIT, "actualRequests": ledger.used,
                "blockedRequests": ledger.blocked, "historicalNoSkillScore": base,
                "historicalValidRepeats": baseline["no_skill_scored"] if baseline is not None else None,
                "score": score, "withSkillScore": score if skill is not None else None,
                "delta": score - base if score is not None and base is not None else None,
                "nativeComment": native.get("comments") or native.get("Comments"),
                "exitCode": process.returncode, "trialStatus": record.get("status"),
                "finishReason": agent.get("finish_reason"), "agentUsage": agent.get("usage"),
                "gradingStatus": (record.get("metrics") or {}).get("grading_status"),
                "skillReadIndices": reads, "skillScriptIndices": scripts,
                "resultPath": str(result_file.relative_to(WORKSPACE)) if result_file else None}
    write_json(output / "summary.json", evidence)
    print(json.dumps(evidence, ensure_ascii=False))
    return 0 if score is not None else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("node_bin", type=Path)
    parser.add_argument("task")
    parser.add_argument("skill", type=Path)
    args = parser.parse_args()
    RESULTS.mkdir(parents=True, exist_ok=True)
    with (RESULTS / ".pilot.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return run_trial(args.project.resolve(), args.node_bin.resolve(), args.task, args.skill.resolve())


if __name__ == "__main__":
    sys.exit(main())
