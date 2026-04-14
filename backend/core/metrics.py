from collections import defaultdict
from typing import Dict, Any

REQUEST_METRICS = {
    "total_requests": 0,
    "status_counts": defaultdict(int),
    "path_counts": defaultdict(int),
    "avg_process_time_ms": 0.0,
}


def record_request(path: str, status_code: int, process_ms: float) -> None:
    REQUEST_METRICS["total_requests"] += 1
    REQUEST_METRICS["status_counts"][str(status_code)] += 1
    REQUEST_METRICS["path_counts"][path] += 1

    total_requests = REQUEST_METRICS["total_requests"]
    previous_avg = REQUEST_METRICS["avg_process_time_ms"]
    REQUEST_METRICS["avg_process_time_ms"] = previous_avg + ((process_ms - previous_avg) / max(total_requests, 1))


def get_metrics_snapshot() -> Dict[str, Any]:
    return {
        "total_requests": REQUEST_METRICS["total_requests"],
        "status_counts": dict(REQUEST_METRICS["status_counts"]),
        "path_counts": dict(REQUEST_METRICS["path_counts"]),
        "avg_process_time_ms": round(float(REQUEST_METRICS["avg_process_time_ms"]), 3),
    }
