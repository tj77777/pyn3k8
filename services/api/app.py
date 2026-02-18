import json
import logging
import os
import uuid
from datetime import datetime, timezone

import requests as http_requests
from flask import Flask, jsonify, request


# Step 1: Define a JSON log formatter for structured logs.
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": "api",
            "message": record.getMessage(),
            "module": record.module,
        }
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)


handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger = logging.getLogger("api")
logger.addHandler(handler)
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

app = Flask(__name__)


# Step 2: Read Worker service URL from environment variables.
WORKER_URL = os.environ.get("WORKER_URL", "http://worker-service:9090")

# Step 3: In-memory storage for demo tasks.
tasks = []


def build_new_task(data):
    # Step 4: Create a new task object with default metadata.
    task_id = str(uuid.uuid4())
    return {
        "id": task_id,
        "name": data.get("name", "unnamed-task"),
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def request_worker_processing(task_id):
    # Step 5: Ask Worker service to process a task id.
    return http_requests.post(
        f"{WORKER_URL}/process",
        json={"task_id": task_id},
        timeout=5,
    )


def apply_worker_result(task, worker_response):
    # Step 6: Merge Worker response into task status fields.
    if worker_response.status_code == 200:
        result = worker_response.json()
        task["status"] = result.get("status", "completed")
        task["processed_at"] = result.get("processed_at")
        task["worker"] = result.get("worker")


@app.route("/healthz")
def healthz():
    # Health endpoint for liveness probe.
    return jsonify({"status": "ok"}), 200


@app.route("/readyz")
def readyz():
    # Health endpoint for readiness probe.
    return jsonify({"status": "ready"}), 200


@app.route("/tasks", methods=["GET"])
def get_tasks():
    # Step 7: Return current task list to UI.
    return jsonify({"tasks": tasks}), 200


@app.route("/tasks", methods=["POST"])
def create_task():
    # Step 8: Read request payload and create a local task record.
    data = request.get_json(silent=True) or {}
    task = build_new_task(data)

    # Step 9: Call Worker service and update task status from Worker response.
    try:
        resp = request_worker_processing(task["id"])
        apply_worker_result(task, resp)
    except Exception as e:
        logger.error("Worker call failed: %s", e)
        task["status"] = "failed"

    # Step 10: Save task and return it to the caller.
    tasks.append(task)
    logger.info("Task %s created with status %s", task["id"], task["status"])
    return jsonify(task), 201
