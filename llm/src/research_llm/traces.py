"""将现有标准 trace 的模型尝试写入账本，并输出不含正文的审核明细。"""

from datetime import UTC, datetime
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path

from .accounting import UsageRecorder, usage_fields


def normalize_trace_usage(harness: str, usage):
    """把 dsh 单独列出的缓存命中 token 还原到含缓存的输入总量。"""
    if harness != "dsh" or not isinstance(usage, dict):
        return usage
    fields = ("input_tokens", "output_tokens", "total_tokens", "cache_read_tokens")
    counts = [usage.get(field) for field in fields]
    if not all(type(count) is int and count >= 0 for count in counts):
        return usage
    input_tokens, output_tokens, total_tokens, cached_tokens = counts
    if (cached_tokens and usage.get("cache_write_tokens") in (None, 0)
            and total_tokens == input_tokens + output_tokens + cached_tokens):
        return {**usage, "input_tokens": input_tokens + cached_tokens}
    return usage


def summarize_calls(rows: list[dict]) -> dict:
    totals = {}
    for row in rows:
        if row["estimated_cost"] is not None:
            currency = row["currency"]
            totals[currency] = totals.get(currency, Decimal(0)) + Decimal(row["estimated_cost"])
    return {
        "calls": len(rows), "unpriced_calls": sum(row["estimated_cost"] is None for row in rows),
        "estimated_totals": {currency: format(amount, "f") for currency, amount in totals.items()},
    }


def import_traces(recorder: UsageRecorder, paths, *, model: str, api_key_env: str = "",
                  base_url: str | None = None, metadata: dict | None = None,
                  log_path: str | Path | None = None, start_offsets: dict | None = None) -> dict:
    """逐次导入已 flush 的 trace，覆盖失败运行和子会话；重复导入不重新计价。"""
    rows = {}
    paths = list(dict.fromkeys(Path(path).resolve() for path in paths))
    if log_path is not None:
        target = Path(log_path).resolve()
        if target in paths or target.with_suffix(target.suffix + ".tmp") in paths or target == recorder.ledger_path:
            raise ValueError("审核日志不能覆盖原 trace 或 SQLite 账本")
    secret = os.environ.get(api_key_env, "")

    def safe(value):
        if isinstance(value, str):
            return value.replace(secret, "[REDACTED]") if secret else value
        if isinstance(value, dict):
            return {key: safe(item) for key, item in value.items()}
        return value

    # 只接受实验归属字段，避免把正文或凭据从调用方 metadata 带入账本。
    metadata = {key: value for key, value in (metadata or {}).items()
                if key in {"experiment_id", "experiment_name", "trial_id", "task_id", "condition", "repeat"}}
    for path in paths:
        with path.open(encoding="utf-8") as stream:
            if start_offsets is not None:
                offset = start_offsets.get(path, 0)
                if path.stat().st_size < offset:
                    raise ValueError(f"运行中的 trace 被截断：{path}")
                stream.seek(offset)
            for line in stream:
                event = json.loads(line)
                if event.get("event") != "model.attempt":
                    continue
                if not all(event.get(key) for key in ("recording_id", "session_id", "event_id")):
                    raise ValueError(f"{path} 的模型尝试缺少稳定标识，无法安全入账")
                identity = [event["recording_id"], event["session_id"], event["event_id"]]
                call_id = "trace-" + hashlib.sha256(json.dumps(identity).encode()).hexdigest()
                data = event.get("data") or {}
                source_status = data.get("status", "unknown")
                status = {"completed": "completed", "committed": "completed", "failed": "failed",
                          "interrupted": "interrupted", "uncommitted": "uncommitted"}.get(source_status, "unknown")
                event_time = event.get("time_ms")
                time_source = "trace_event"
                if not isinstance(event_time, (int, float)) or isinstance(event_time, bool):
                    event_time = event.get("observed_at_ms")
                    time_source = "recorder_observed"
                if not isinstance(event_time, (int, float)) or isinstance(event_time, bool):
                    raise ValueError(f"{path} 的模型尝试缺少时间")
                timestamp = datetime.fromtimestamp(event_time / 1000, UTC).isoformat(timespec="microseconds")
                observed_model = safe((event.get("model") or {}).get("model") or model)
                error = data.get("error")
                row = recorder.record_usage(
                    model=observed_model, api_key_env=safe(api_key_env), base_url=base_url,
                    usage=usage_fields(normalize_trace_usage(event.get("harness"), data.get("usage"))),
                    status=status, source_status=source_status,
                    source=event.get("harness") or "trace", call_id=call_id,
                    started_at=timestamp, finished_at=timestamp, time_source=time_source,
                    response_model=observed_model, response_id=safe(data.get("response_id")),
                    error_type=error.get("type") if isinstance(error, dict) else None,
                    metadata=safe({**metadata, "recording_id": event["recording_id"],
                              "run_id": event.get("run_id"), "session_id": event["session_id"],
                              "attempt_id": event.get("attempt_id"), "event_id": event["event_id"],
                              "configured_model": model}),
                )
                rows[call_id] = row
    if log_path is not None:
        path = Path(log_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        with temporary.open("w", encoding="utf-8", newline="\n") as stream:
            for row in rows.values():
                # JSON 日志展开 JSON 字段，便于直接核对价格和实验归属。
                audit = dict(row)
                audit["rates_per_million"] = json.loads(audit["rates_per_million"]) if audit["rates_per_million"] else None
                audit["pricing_rule"] = json.loads(audit.pop("pricing_rule_json") or "null")
                audit["metadata"] = json.loads(audit.pop("metadata_json") or "{}")
                stream.write(json.dumps(audit, ensure_ascii=False, allow_nan=False) + "\n")
        temporary.replace(path)
    return {**summarize_calls(list(rows.values())), "ledger_path": str(recorder.ledger_path),
            "log_path": str(Path(log_path).resolve()) if log_path is not None else None}
