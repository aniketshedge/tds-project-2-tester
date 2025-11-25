import logging
import os
import random
from logging.handlers import RotatingFileHandler

import requests
import httpx
from flask import Flask, jsonify, render_template, request
from openai import OpenAI
from dotenv import load_dotenv


load_dotenv()

app = Flask(__name__)

# File-based logging (for debugging on the server)
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

log_path = os.path.join(LOG_DIR, "mock_server.log")
file_handler = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=3)
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
file_handler.setFormatter(formatter)

logger = app.logger
logger.handlers.clear()
logger.addHandler(file_handler)
logger.setLevel(logging.INFO)


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-nano")
OPENAI_INSECURE_SKIP_VERIFY = (
    os.getenv("OPENAI_INSECURE_SKIP_VERIFY", "false").lower() in ("1", "true", "yes")
)

if OPENAI_API_KEY:
    http_client = None
    if OPENAI_INSECURE_SKIP_VERIFY:
        # Development-only: disable TLS verification for custom/self-signed endpoints.
        http_client = httpx.Client(verify=False)

    client_kwargs: dict = {"api_key": OPENAI_API_KEY}
    if OPENAI_BASE_URL:
        client_kwargs["base_url"] = OPENAI_BASE_URL
    if http_client is not None:
        client_kwargs["http_client"] = http_client

    client = OpenAI(**client_kwargs)
else:
    client = None

logger.info(
    "mock_server starting with model=%s base_url=%s insecure_skip_verify=%s client_configured=%s",
    OPENAI_MODEL,
    OPENAI_BASE_URL,
    OPENAI_INSECURE_SKIP_VERIFY,
    bool(client),
)


current_quiz_html = "<h1>Welcome</h1><p>Waiting for a challenge...</p>"
received_submissions = []


TASK_TYPES = [
    "Data Parsing: Extract data from a messy HTML table and sum a column.",
    "Vision: Provide a description of a chart (simulated via text description or placeholder image) and ask for a trend.",
    "Pattern Matching: Find a hidden code inside a block of random text.",
    "Data Cleaning: Fix valid JSON hidden inside broken text.",
    "Security: A prompt injection test asking the agent to reveal a secret.",
]


@app.route("/")
def dashboard():
    return render_template("index.html", server_url=request.host_url)


@app.route("/api/generate", methods=["POST"])
def generate_question():
    if not client:
        return jsonify({"error": "No OpenAI Key configured"}), 500

    task_type = random.choice(TASK_TYPES)

    system_prompt = (
        "You are a chaos engineering test generator for a Data Analysis Agent. "
        "Generate a challenging HTML snippet (divs, tables, h2, p) for a quiz task. "
        "Do NOT include <html> or <body> tags. "
        "Do NOT include the 'Post your answer to...' submission instructions (the server handles that). "
        "Include actual dummy data (tables, text) within the HTML so the agent has something to process."
    )

    user_prompt = f"Generate a task involving: {task_type}. Keep it concise."

    try:
        logger.info(
            "api_generate: requesting quiz HTML from model=%s task_type=%s",
            OPENAI_MODEL,
            task_type,
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        completion_kwargs = {
            "model": OPENAI_MODEL,
            "messages": messages,
        }

        # For reasoning-capable models like gpt-5.1, opt into low effort by default.
        if OPENAI_MODEL.startswith("gpt-5.1"):
            completion_kwargs["effort"] = "low"

        response = client.chat.completions.create(**completion_kwargs)
        html_content = response.choices[0].message.content
        html_content = html_content.replace("```html", "").replace("```", "")
        logger.info(
            "api_generate: received HTML length=%d snippet=%r",
            len(html_content),
            html_content[:200],
        )
        return jsonify({"html": html_content})
    except Exception as exc:  # noqa: BLE001
        # Log full details to the server console to aid debugging
        logger.exception("Error while calling OpenAI for quiz generation")
        return jsonify({"error": str(exc)}), 500


@app.route("/set_quiz", methods=["POST"])
def set_quiz():
    global current_quiz_html

    data = request.get_json(silent=True) or {}
    current_quiz_html = data.get("html", "") or ""
    logger.info(
        "set_quiz: updated quiz HTML length=%d snippet=%r",
        len(current_quiz_html),
        current_quiz_html[:200],
    )
    received_submissions.clear()
    return jsonify({"status": "updated"})


@app.route("/quiz")
def render_quiz():
    submit_url = request.host_url + "submit"
    logger.info(
        "render_quiz: current_quiz_html length=%d snippet=%r",
        len(current_quiz_html),
        current_quiz_html[:200],
    )
    injected_footer = f"""
    <hr>
    <div style="background: #f0f0f0; padding: 15px; border-top: 2px solid #333;">
        <h4>Submission Instructions</h4>
        <p>Post your answer to: <code>{submit_url}</code></p>
        <pre style="background:#ddd; padding:10px;">
{{
  "email": "student@example.com",
  "secret": "TEST_SECRET",
  "url": "{request.url}",
  "answer": "YOUR_ANSWER_HERE"
}}
        </pre>
    </div>
    """
    return current_quiz_html + injected_footer


@app.route("/submit", methods=["POST"])
def handle_submission():
    data = request.get_json(silent=True)
    logger.info(
        "submit: received payload type=%s keys=%s",
        type(data).__name__,
        sorted(list(data.keys())) if isinstance(data, dict) else None,
    )
    received_submissions.insert(0, {"payload": data})
    return jsonify({"correct": True, "message": "Mock Server: Correct!"})


@app.route("/api/submissions")
def get_submissions():
    return jsonify(received_submissions)


@app.route("/api/send", methods=["POST"])
def send_test_payload():
    """Send a test POST payload to a student Agent endpoint."""
    data = request.get_json(silent=True) or {}

    endpoint = data.get("endpoint")
    email = data.get("email") or "student@example.com"
    secret = data.get("secret") or "TEST_SECRET"

    if not endpoint:
        return jsonify({"error": "Missing 'endpoint' in request body"}), 400

    quiz_url = request.host_url.rstrip("/") + "/quiz"

    payload = {
        "email": email,
        "secret": secret,
        "url": quiz_url,
    }

    try:
        logger.info(
            "api_send: posting to endpoint=%s with payload=%r",
            endpoint,
            payload,
        )
        resp = requests.post(endpoint, json=payload, timeout=15)
        logger.info(
            "api_send: got status_code=%s response_length=%d",
            resp.status_code,
            len(resp.text),
        )
        return jsonify(
            {
                "ok": True,
                "status_code": resp.status_code,
                "response_body": resp.text,
            }
        )
    except requests.RequestException as exc:  # noqa: BLE001
        logger.exception("api_send: error posting to endpoint")
        return jsonify({"error": str(exc)}), 502


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9000, debug=True)
