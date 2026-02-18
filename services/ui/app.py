import json
import logging
import os
from datetime import datetime, timezone

import requests as http_requests
from flask import Flask, jsonify, render_template, request



# Step 1: Define a JSON log formatter so logs are easy to parse in Kubernetes.
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": "ui",
            "message": record.getMessage(),
            "module": record.module,
        }
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)


handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger = logging.getLogger("ui")
logger.addHandler(handler)
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

app = Flask(__name__)

# Step 2: Read the API base URL from environment variables.
API_URL = os.environ.get("API_URL", "http://api-service:8080")


def fetch_tasks_from_api():
    # Step 3: UI requests the task list from API service.
    response = http_requests.get(f"{API_URL}/tasks", timeout=5)
    if response.status_code == 200:
        return response.json().get("tasks", [])
    return []


def create_task_in_api(name):
    # Step 4: UI forwards a create-task request to API service.
    return http_requests.post(
        f"{API_URL}/tasks",
        json={"name": name},
        timeout=5,
    )


@app.route("/healthz")
def healthz():
    # Health endpoint for liveness probe.
    return jsonify({"status": "ok"}), 200


@app.route("/readyz")
def readyz():
    # Health endpoint for readiness probe.
    return jsonify({"status": "ready"}), 200


@app.route("/", methods=["GET"])
def index():
    # Step 5: Render the UI page with tasks fetched from API.
    tasks = []
    error = None
    try:
        tasks = fetch_tasks_from_api()
    except Exception as e:
        logger.error("API call failed: %s", e)
        error = str(e)
    return render_template("index.html", tasks=tasks, error=error)


@app.route("/create", methods=["POST"])
def create_task():
    # Step 6: Read task name from form, call API, then render updated list.
    name = request.form.get("name", "unnamed-task")
    try:
        create_task_in_api(name)
    except Exception as e:
        logger.error("API call failed: %s", e)
    return index()
