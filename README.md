# Examiner Mock Tool ("The Gym") – Tester for LLM Analysis Quiz

This repository contains a **local tester tool** for the *LLM Analysis Quiz* project described in `project-brief.md`.

Your actual graded project (the Agent / API endpoint) lives in a **separate repository**. This repo gives you a realistic, controllable environment to:

- Host quiz pages locally (including JavaScript-rendered content).
- Generate new quiz tasks automatically using `gpt-5-nano`.
- Capture and inspect the JSON submissions your Agent sends.

Think of this as **"the gym"** where you train and debug your Agent before it faces the real evaluation server.

---

## 1. High-Level Overview

From `project-brief.md`, your Agent must:

- Accept a POST payload containing `email`, `secret`, and `url`.
- Validate the `secret`.
- Visit the quiz page at `url` (which may use JavaScript).
- Extract and process data (scraping, parsing PDFs, cleaning text/JSON, analysis, visualization, etc.).
- POST the correct answer as JSON to the submission URL indicated on the quiz page.
- Potentially follow **multiple quiz URLs** in sequence within a 3-minute window.

This repo implements a **mock evaluation server** that behaves similarly, but locally:

- Serves a **dashboard UI** at `/` for creating and managing quiz pages.
- Hosts the **current quiz page** at `/quiz`.
- Provides a **submission endpoint** at `/submit`.
- Records all submissions and exposes them via `/api/submissions` (shown in the dashboard).
- Optionally uses `gpt-5-nano` via the OpenAI API to generate random, realistic quiz snippets.

You point your Agent at the `/quiz` URL from this tool and iterate until it reliably solves a variety of tasks.

---

## 2. Repository Structure

```text
.
├── project-brief.md      # Original course project description (your Agent spec)
├── tester-blueprint.md   # Design document for this tester tool (The Gym)
└── mock-tool/
    ├── mock_server.py    # Flask server: routes, state, and OpenAI integration
    ├── requirements.txt  # Python dependencies
    └── templates/
        └── index.html    # Vue.js + Quill UI dashboard
```

Your primary interaction points in this repo are:

- `mock-tool/mock_server.py`
- `mock-tool/templates/index.html`
- `mock-tool/requirements.txt`

---

## 3. Features

- **Quiz Builder UI**
  - Rich-text editor (Quill) to author HTML quiz content.
  - "✨ Generate Random Question" button that calls OpenAI’s `gpt-5-nano` to create a fresh quiz snippet based on predefined task types (scraping, vision, data cleaning, prompt injection, etc.).
  - One-click deployment of the quiz to the `/quiz` endpoint.

- **Mock Evaluation Flow**
  - `/quiz` endpoint serves the current quiz HTML.
  - Automatically appends **submission instructions** with a JSON payload template and a concrete `/submit` URL.
  - Your Agent interacts with `/quiz` exactly as it would with the remote evaluation server.

- **Submission Capture & Inspection**
  - `/submit` endpoint records every JSON payload your Agent sends.
  - `/api/submissions` returns them as a list (latest first).
  - Dashboard UI shows:
    - The `answer` field prominently.
    - The **entire JSON payload** in an expandable view.
  - Live-updating view (polls every 2 seconds).

- **OpenAI-Powered Test Generation**
  - Uses `OPENAI_API_KEY` and the `openai` Python library.
  - Generates HTML-only snippets (no `<html>`/`<body>` tags) with dummy data to process.
  - Strips markdown code fences if the model returns them.

---

## 4. Backend Architecture (`mock_server.py`)

Location: `mock-tool/mock_server.py`

### 4.1. Tech Stack

- **Language:** Python 3.10+
- **Web Framework:** Flask
- **Environment Management:** `python-dotenv`
- **LLM Client:** `openai` (via `OpenAI` class)

### 4.2. Global State

- `current_quiz_html`  
  - A string holding the currently deployed quiz HTML snippet.
  - Defaults to: `"<h1>Welcome</h1><p>Waiting for a challenge...</p>"`.

- `received_submissions`  
  - An in-memory list of records like `{"payload": <JSON from agent>}`.
  - New submissions are inserted at the **front** (index 0), so the latest appears first.

> Note: This tool is meant for local, manual use only. No persistence or concurrency guarantees.

### 4.3. Task Types

The server randomly picks a task type when generating a question:

- Data parsing from messy HTML tables.
- Vision-style description and trend extraction.
- Pattern matching and hidden code detection.
- Data cleaning of broken JSON.
- Basic prompt-injection / security scenario.

You can inspect and customize these in `TASK_TYPES` inside `mock_server.py`.

### 4.4. Routes

#### `GET /`

- Renders `templates/index.html`.
- Passes `server_url=request.host_url` into the template (if needed).

#### `POST /api/generate`

- **Purpose:** Ask `gpt-5-nano` to generate a new quiz HTML snippet.
- **Request Body:** Empty JSON body is fine; only method must be POST.
- **Behavior:**
  - If `OPENAI_API_KEY` is **not** configured, returns:
    ```json
    { "error": "No OpenAI Key configured" }
    ```
    with HTTP `500`.
  - Selects a random `TASK_TYPE`.
  - Sends a system + user prompt to `gpt-5-nano` describing:
    - The need for a challenging HTML snippet (e.g., `<div>`, `<table>`, `<h2>`, `<p>`).
    - No `<html>` or `<body>` tags.
    - No explicit "Post your answer to..." instructions (the server injects that).
    - Include actual dummy data.
  - Extracts `response.choices[0].message.content`.
  - Strips markdown fences like ``` ```html ``` if present.
- **Response (success):**
  ```json
  { "html": "<h2>Task...</h2><p>...</p>" }
  ```

#### `POST /set_quiz`

- **Purpose:** Deploy a new quiz HTML snippet.
- **Request Body:**
  ```json
  { "html": "<h2>My Quiz</h2><p>...</p>" }
  ```
- **Behavior:**
  - Stores `html` as `current_quiz_html` (empty string if missing).
  - Clears any existing `received_submissions`.
- **Response:**
  ```json
  { "status": "updated" }
  ```

#### `GET /quiz`

- **Purpose:** Serve the current quiz HTML to your Agent.
- **Behavior:**
  - Starts with `current_quiz_html`.
  - Appends an "injected footer" containing:
    - A clear "Submission Instructions" header.
    - Exact JSON payload template, e.g.:
      ```jsonc
      {
        "email": "student@example.com",
        "secret": "TEST_SECRET",
        "url": "http://localhost:9000/quiz",
        "answer": "YOUR_ANSWER_HERE"
      }
      ```
    - The correct `submit` URL to POST to (computed as `request.host_url + "submit"`).
- **Response:**
  - A full HTML fragment string: your quiz + the injected footer.

Your Agent should:

- Load this page (possibly with a headless browser).
- Extract the question and data from the quiz content.
- Read the **submission instructions** from the footer.
- POST the correct JSON payload to that URL.

#### `POST /submit`

- **Purpose:** Accept and log Agent submissions.
- **Request Body:** Arbitrary JSON. Commonly:
  ```jsonc
  {
    "email": "student@example.com",
    "secret": "TEST_SECRET",
    "url": "http://localhost:9000/quiz",
    "answer": 12345
  }
  ```
- **Behavior:**
  - Parses the JSON body (using `request.get_json(silent=True)`).
  - Inserts `{ "payload": <body> }` at the front of `received_submissions`.
- **Response:**
  ```json
  {
    "correct": true,
    "message": "Mock Server: Correct!"
  }
  ```

> For now, this endpoint always returns `correct: true`. The focus is on verifying that your Agent **finds, understands, and hits the right endpoint with the right shape of payload**, not on strict auto-grading.

#### `GET /api/submissions`

- **Purpose:** Expose all received submissions.
- **Response:**
  ```json
  [
    { "payload": { /* most recent submission */ } },
    { "payload": { /* older submission */ } }
  ]
  ```

The UI polls this endpoint every 2 seconds to update the "Agent Submissions" panel.

---

## 5. Frontend Architecture (`templates/index.html`)

Location: `mock-tool/templates/index.html`

### 5.1. Tech Stack

- HTML5 + Bootstrap 5 (for layout and styling).
- Vue.js 2 (CDN).
- Quill.js rich-text editor (CDN).

### 5.2. Layout

- **Left Panel – 1. Quiz Builder**
  - Quill editor (`#editor-container`) where you type or paste quiz HTML.
  - Button **"✨ Generate Random Question"**:
    - Calls `generateAI()` in Vue.
    - Sends `POST /api/generate`.
    - If `data.html` is present, inserts it into the editor using `quill.clipboard.dangerouslyPasteHTML`.
  - Button **"Update / Deploy Quiz Page"**:
    - Calls `deployQuiz()` in Vue.
    - Sends `POST /set_quiz` with `{ html: quill.root.innerHTML }`.
    - Alerts `Quiz Live!` on success.
  - Shows the **Target URL** (`quizUrl`) that your Agent should use.

- **Left Panel – 2. Trigger Agent Endpoint**
  - Small form to **manually enter**:
    - Your Agent **endpoint URL** (the app that implements the project brief).
    - Your **email**.
    - Your **secret**.
  - Button **"Send Test Payload"**:
    - Calls `/api/send` on this tester.
    - The tester server then sends a POST payload to your Agent endpoint:
      ```jsonc
      {
        "email": "<email you entered>",
        "secret": "<secret you entered>",
        "url": "http://localhost:9000/quiz" // or whatever your tester base URL is
      }
      ```
    - The Agent should then:
      - Validate the secret.
      - Visit the provided `url` (the tester’s `/quiz`).
      - Solve the quiz and POST the answer to the submit URL given on that page.

- **Right Panel – 2. Agent Submissions**
  - Displays a card per submission:
    - A highlighted `Answer Received:` block showing `sub.payload.answer`.
    - A `<details>` block containing `JSON.stringify(sub.payload, null, 2)` for full inspection.
  - If there are no submissions, shows a friendly `"No data yet"` message.
  - Polls `/api/submissions` every 2 seconds via `setInterval(this.fetchSubmissions, 2000)`.

---

## 6. Installation & Setup

### 6.1. Prerequisites

- Python **3.10+**
- `pip` (or other Python package manager)
- An OpenAI API key with access to `gpt-5-nano` (for the "Generate Random Question" feature).

### 6.2. Install Dependencies

From the root of this repo:

```bash
cd mock-tool
pip install -r requirements.txt
```

### 6.3. Configure Environment

Create a `.env` file in `mock-tool/` (you can copy from `.env.example`):

```env
OPENAI_API_KEY=sk-your-api-key-here

# Optional: point to a custom OpenAI-compatible endpoint
# For example, a proxy or self-hosted server that speaks the same API.
# If omitted, the official OpenAI API base URL is used by default.
# OPENAI_BASE_URL=https://your-custom-endpoint.example.com/v1

# Optional: override the model used by the tester.
# Defaults to gpt-5-nano. For reasoning models like gpt-5.1, the tester
# will automatically set effort=low for generations.
# OPENAI_MODEL=gpt-5.1

# Optional: development-only TLS bypass for self-signed / intercepted HTTPS.
# DO NOT enable this in production; it disables certificate verification for
# OpenAI requests made by this tester.
# OPENAI_INSECURE_SKIP_VERIFY=false
```

The `mock-tool/.env.example` file is tracked in git and serves as a template.  
The real `mock-tool/.env` file is **not** tracked (ignored via the root `.gitignore`) so your secrets stay local while CI/CD and systemd continue to load them.

- If `OPENAI_API_KEY` is **missing or invalid**, the app still runs, but:
  - `POST /api/generate` returns an error.
  - The "✨ Generate Random Question" button will show an alert with that error.
  - You can still manually author quizzes in the editor and deploy them.

---

## 7. Running the Mock Server

From the root of the repo:

```bash
cd mock-tool
python mock_server.py
```

By default, Flask runs at:

- `http://localhost:9000`

Key URLs:

- Dashboard UI: `http://localhost:9000/`
- Quiz URL (Target for your Agent): `http://localhost:9000/quiz`
- Submission endpoint: `http://localhost:9000/submit`

---

## 8. Using the UI (Step-by-Step)

1. **Start the server**  
   - Run `python mock_server.py` and confirm it’s listening on port 9000.

2. **Open the dashboard**  
   - Visit `http://localhost:9000` in your browser.

3. **Create or generate a quiz**
   - Option A – Manual:
     - Type or paste HTML into the editor.
     - Include any tables, text, embedded JSON, or instructions you want.
   - Option B – Auto-generate:
     - Click **"✨ Generate Random Question"**.
     - Wait for the model to return HTML.
     - Edit the generated content if desired.

4. **Deploy the quiz**
   - Click **"Update / Deploy Quiz Page"**.
   - An alert `Quiz Live!` confirms success.
   - The "Target URL" box shows the `/quiz` URL; this is what you feed your Agent.

5. **Run your Agent**
   - In the **Trigger Agent Endpoint** section:
     - Enter your Agent endpoint URL (where your project listens).
     - Enter your email and secret (the same ones you’ll submit in the Google Form).
     - Click **"Send Test Payload"**.
   - The tester will POST the payload to your Agent with `url` set to the tester’s `/quiz` URL.
   - Your Agent should now:
     - Validate `secret`.
     - Visit the given `url` (the quiz page hosted by this tester).
     - Follow the instructions on that page and submit the answer to the indicated submit URL.

6. **Inspect submissions**
   - Watch the right-hand panel (“Agent Submissions”) update every 2 seconds.
   - For each submission:
     - Check the `answer` field for sanity.
     - Expand "Full Payload" to see the complete JSON, including:
       - `email`
       - `secret`
       - `url`
       - `answer`
       - Any additional fields you choose to include.

7. **Iterate**
   - Modify your Agent or quiz content.
   - Redeploy quizzes and re-run until your Agent behaves robustly across different question types.

---

## 9. Integrating Your Agent with The Gym

Although your Agent’s full implementation lives elsewhere, this tool is designed to mimic the evaluation server’s behavior so you can test the entire pipeline.

### 9.1. Typical Local Testing Flow

1. **Simulate the evaluation server’s POST to your Agent**  
   - Use the **"Send Test Payload"** button in the tester UI, or manually send:
     ```jsonc
     {
       "email": "you@university.edu",
       "secret": "YOUR_AGENT_SECRET",
       "url": "http://localhost:9000/quiz"
     }
     ```
   - Your Agent validates `"secret"` and then loads `"url"`.

2. **Agent processes the quiz page**
   - Loads `http://localhost:9000/quiz` (headless browser or HTML+JS rendering).
   - Waits for any DOM-manipulating scripts (if you add them).
   - Parses:
     - The main quiz content you wrote or generated.
     - The injected "Submission Instructions" footer.

3. **Agent constructs an answer payload**
   - Reads the example payload in the footer.
   - Fills in:
     - `email` (your own).
     - `secret` (your secret).
     - `url` (the quiz URL).
     - `answer` (whatever the question expects).

4. **Agent POSTs to the indicated submit URL**
   - Usually something like:
     - `http://localhost:9000/submit`
   - This tool logs the submission and returns:
     ```json
     {
       "correct": true,
       "message": "Mock Server: Correct!"
     }
     ```

5. **Verify behavior in the dashboard**
   - Confirm your Agent:
     - Found the submit URL correctly (no hardcoding to remote domains).
     - Built the correct payload shape.
     - Can handle repeated runs and different question types.

---

## 10. Customization Ideas

You can extend this mock server to better match how you design your Agent:

- **More complex question templates**
  - Add new entries to `TASK_TYPES` (e.g., PDF-based tasks, multi-step chains, API calls).
  - Adjust the LLM `system_prompt` to emphasize certain structures (tables, nested lists, embedded JSON).

- **Rudimentary auto-grading**
  - Modify `/submit` to:
    - Store an "expected" answer along with `current_quiz_html`.
    - Compare `payload["answer"]` to that expected value.
    - Return `correct: true/false` and a helpful message.

- **Multiple quizzes / sessions**
  - Track multiple `current_quiz_html` instances by session key.
  - Add query parameters (e.g., `/quiz?session=123`) and store submissions under that key.

---

## 11. Troubleshooting

- **"python: command not found" or version issues**
  - Ensure Python 3.10+ is installed and `python` or `python3` points to it.
  - On some systems, you may need:
    - `python3 mock_server.py`

- **Cannot import Flask / openai / dotenv**
  - Double-check you ran:
    ```bash
    cd mock-tool
    pip install -r requirements.txt
    ```

- **"No OpenAI Key configured" when clicking "Generate Random Question"**
  - Ensure `.env` in `mock-tool/` contains:
    ```env
    OPENAI_API_KEY=sk-your-api-key-here
    ```
  - If you use a custom endpoint, also verify:
    ```env
    OPENAI_BASE_URL=https://your-custom-endpoint.example.com/v1
    ```
   - If you see TLS / certificate errors (e.g. `self-signed certificate in certificate chain`)
     in your terminal logs and you are in a controlled dev environment with a proxy or
     self-signed gateway, you can temporarily set:
     ```env
     OPENAI_INSECURE_SKIP_VERIFY=true
     ```
     (Restart the server after changing this.) This disables TLS verification only for
     the tester’s calls to the OpenAI-compatible endpoint.
  - Restart the server after editing `.env`.

- **Agent submissions not appearing**
  - Confirm your Agent is POSTing to the URL shown in the quiz footer (usually `/submit` on `localhost:9000`).
  - Check browser dev tools → Network tab for `/api/submissions` requests and responses.
  - Manually `curl` the endpoint to validate:
    ```bash
    curl -X POST http://localhost:9000/submit \
         -H "Content-Type: application/json" \
         -d '{"answer": "test"}'
    ```
    Then refresh the UI and verify that "test" appears as an answer.

---

## 12. Next Steps

Once this mock tool is up and running smoothly with your Agent:

- Point your Agent at the **real evaluation server** described in `project-brief.md`.
- Ensure:
  - Timeouts and retries are handled properly (within 3 minutes).
  - Your Agent correctly follows new `url` fields returned from the server.
  - Your prompt strategies (system + user prompts) are robust against prompt injection and other adversarial content.

Use this repo as a safe sandbox to explore edge cases and improve your Agent’s reliability before final evaluation.
