import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone

from flask import Flask, jsonify, request


# Step 1: Define a JSON log formatter for consistent logs.
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": "worker",
            "message": record.getMessage(),
            "module": record.module,
        }
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)


handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger = logging.getLogger("worker")
logger.addHandler(handler)
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

app = Flask(__name__)


def process_task(task_id):
    # Step 2: Simulate processing work for the given task id.
    logger.info("Processing task %s", task_id)
    time.sleep(0.5)
    return {
        "task_id": task_id,
        "status": "completed",
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "worker": os.environ.get("HOSTNAME", "unknown"),
    }


@app.route("/healthz")
def healthz():
    # Health endpoint for liveness probe.
    return jsonify({"status": "ok"}), 200


@app.route("/readyz")
def readyz():
    # Health endpoint for readiness probe.
    return jsonify({"status": "ready"}), 200


@app.route("/process", methods=["POST"])
def process():
    # Step 3: Read task id from API request.
    data = request.get_json(silent=True) or {}
    task_id = data.get("task_id", str(uuid.uuid4()))

    # Step 4: Process and return result payload to API service.
    result = process_task(task_id)
    return jsonify(result), 200
