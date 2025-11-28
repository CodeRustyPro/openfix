"""Metrics collection for Phase 1."""
import json
import time
from pathlib import Path
from typing import Dict, Any

class Metrics:
    def __init__(self):
        self.metrics: Dict[str, Any] = {
            "retrieval_precision": 0.0,
            "patch_attempts": 0,
            "patch_successes": 0,
            "token_usage": 0,
            "total_time": 0.0,
            "start_time": time.time()
        }

    def record_retrieval(self, precision: float):
        self.metrics["retrieval_precision"] = precision

    def record_attempt(self, success: bool, tokens: int):
        self.metrics["patch_attempts"] += 1
        if success:
            self.metrics["patch_successes"] += 1
        self.metrics["token_usage"] += tokens

    def save(self, path: str):
        self.metrics["total_time"] = time.time() - self.metrics["start_time"]
        with open(path, 'w') as f:
            json.dump(self.metrics, f, indent=2)

    def get(self) -> Dict[str, Any]:
        return self.metrics
