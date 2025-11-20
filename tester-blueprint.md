# **Project Blueprint: Examiner Mock Tool ("The Gym") v2**

## **1\. Executive Summary**

A minimal web application that simulates the Evaluation Server. It provides a UI to manually **or automatically** generate quiz pages, hosts them locally, and captures the Agent's submissions.

This is made to test the project describe the **project-brief.md** file. The project is created in another repository, and this one is designed to test that.

* **New Feature:** "Generate Random Question" button uses gpt-5-nano to create diverse, realistic data tasks (scraping, analysis, vision) based on the project brief.

## **2\. Technical Stack**

* **Language:** Python 3.10+  
* **Framework:** Flask.  
* **Frontend:** HTML5 \+ Quill.js \+ Vue.js.  
* **AI Integration:** openai library (Model: gpt-5-nano).

## **3\. File Structure**

Plaintext

mock-tool/  
├── mock\_server.py      \# Flask logic \+ OpenAI Generation  
├── templates/  
│   └── index.html      \# UI with "Generate AI Question" button  
├── .env                \# Needs OPENAI\_API\_KEY  
└── requirements.txt    \# flask, openai, python-dotenv

## **4\. Implementation Details**

### **A. requirements.txt**

Plaintext

flask  
openai  
python-dotenv

### **B. mock\_server.py**

Updated to include the /api/generate endpoint.

Python

import os  
import random  
from flask import Flask, request, render\_template, jsonify  
from openai import OpenAI  
from dotenv import load\_dotenv

load\_dotenv()

app \= Flask(\_\_name\_\_)

\# Configuration  
OPENAI\_API\_KEY \= os.getenv("OPENAI\_API\_KEY")  
client \= OpenAI(api\_key=OPENAI\_API\_KEY) if OPENAI\_API\_KEY else None

\# STATE  
current\_quiz\_html \= "\<h1\>Welcome\</h1\>\<p\>Waiting for a challenge...\</p\>"  
received\_submissions \= \[\]

\# TASK TYPES from Project Brief  
TASK\_TYPES \= \[  
    "Data Parsing: Extract data from a messy HTML table and sum a column.",  
    "Vision: Provide a description of a chart (simulated via text description or placeholder image) and ask for a trend.",  
    "Pattern Matching: Find a hidden code inside a block of random text.",  
    "Data Cleaning: Fix valid JSON hidden inside broken text.",  
    "Security: A prompt injection test asking the agent to reveal a secret.",  
\]

@app.route('/')  
def dashboard():  
    return render\_template('index.html', server\_url=request.host\_url)

@app.route('/api/generate', methods=\['POST'\])  
def generate\_question():  
    """Uses GPT-5-nano to invent a quiz question."""  
    if not client:  
        return jsonify({"error": "No OpenAI Key configured"}), 500

    task\_type \= random.choice(TASK\_TYPES)  
      
    system\_prompt \= (  
        "You are a chaos engineering test generator for a Data Analysis Agent. "  
        "Generate a challenging HTML snippet (divs, tables, h2, p) for a quiz task. "  
        "Do NOT include \<html\> or \<body\> tags. "  
        "Do NOT include the 'Post your answer to...' submission instructions (the server handles that). "  
        "Include actual dummy data (tables, text) within the HTML so the agent has something to process."  
    )  
      
    user\_prompt \= f"Generate a task involving: {task\_type}. Keep it concise."

    try:  
        response \= client.chat.completions.create(  
            model="gpt-5-nano",  
            messages=\[  
                {"role": "system", "content": system\_prompt},  
                {"role": "user", "content": user\_prompt}  
            \],  
            temperature=0.8,  
            max\_tokens=500  
        )  
        html\_content \= response.choices\[0\].message.content  
        \# Strip markdown fencing if present  
        html\_content \= html\_content.replace("\`\`\`html", "").replace("\`\`\`", "")  
        return jsonify({"html": html\_content})  
    except Exception as e:  
        return jsonify({"error": str(e)}), 500

@app.route('/set\_quiz', methods=\['POST'\])  
def set\_quiz():  
    global current\_quiz\_html  
    data \= request.json  
    current\_quiz\_html \= data.get('html', '')  
    received\_submissions.clear()  
    return jsonify({"status": "updated"})

@app.route('/quiz')  
def render\_quiz():  
    submit\_url \= request.host\_url \+ "submit"  
    \# Auto-inject instructions  
    injected\_footer \= f"""  
    \<hr\>  
    \<div style="background: \#f0f0f0; padding: 15px; border-top: 2px solid \#333;"\>  
        \<h4\>Submission Instructions\</h4\>  
        \<p\>Post your answer to: \<code\>{submit\_url}\</code\>\</p\>  
        \<pre style="background:\#ddd; padding:10px;"\>  
{{  
  "email": "student@example.com",  
  "secret": "TEST\_SECRET",  
  "url": "{request.url}",  
  "answer": "YOUR\_ANSWER\_HERE"  
}}  
        \</pre\>  
    \</div\>  
    """  
    return current\_quiz\_html \+ injected\_footer

@app.route('/submit', methods=\['POST'\])  
def handle\_submission():  
    data \= request.json  
    received\_submissions.insert(0, {"payload": data})  
    return jsonify({"correct": True, "message": "Mock Server: Correct\!"})

@app.route('/api/submissions')  
def get\_submissions():  
    return jsonify(received\_submissions)

if \_\_name\_\_ \== '\_\_main\_\_':  
    app.run(host='0.0.0.0', port=9000, debug=True)

### **C. templates/index.html**

Added the "Generate AI Question" button with a loading state.

HTML

\<\!DOCTYPE **html**\>  
\<html lang\="en"\>  
\<head\>  
    \<meta charset\="UTF-8"\>  
    \<title\>Examiner Mock Tool\</title\>  
    \<link href\="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel\="stylesheet"\>  
    \<link href\="https://cdn.quilljs.com/1.3.6/quill.snow.css" rel\="stylesheet"\>  
    \<style\>  
        body { background-color: \#f4f6f8; }  
        \#editor-container { height: 400px; background: white; }  
        .pre-wrap { white-space: pre-wrap; }  
    \</style\>  
\</head\>  
\<body\>  
\<div class\="container-fluid p-4" id\="app"\>  
    \<div class\="row"\>  
        \<div class\="col-md-6"\>  
            \<div class\="card h-100"\>  
                \<div class\="card-header bg-primary text-white d-flex justify-content-between align-items-center"\>  
                    \<strong\>1\. Quiz Builder\</strong\>  
                    \<button class\="btn btn-sm btn-warning fw-bold" @click\="generateAI" :disabled\="loading"\>  
                        \<span v-if\="loading"\>Generating...\</span\>  
                        \<span v-else\>✨ Generate Random Question\</span\>  
                    \</button\>  
                \</div\>  
                \<div class\="card-body d-flex flex-column"\>  
                    \<div id\="editor-container"\>\</div\>  
                    \<button class\="btn btn-success mt-3" @click\="deployQuiz"\>  
                        Update / Deploy Quiz Page  
                    \</button\>  
                    \<div class\="mt-3 p-2 bg-light border rounded"\>  
                        \<small\>Target URL: \<a :href\="quizUrl" target\="\_blank"\>{{ quizUrl }}\</a\>\</small\>  
                    \</div\>  
                \</div\>  
            \</div\>  
        \</div\>

        \<div class\="col-md-6"\>  
            \<div class\="card h-100"\>  
                \<div class\="card-header bg-dark text-white d-flex justify-content-between"\>  
                    \<span\>2\. Agent Submissions\</span\>  
                    \<button class\="btn btn-sm btn-outline-light" @click\="fetchSubmissions"\>Refresh\</button\>  
                \</div\>  
                \<div class\="card-body overflow-auto" style\="max-height: 80vh;"\>  
                    \<div v-for\="(sub, index) in submissions" :key\="index" class\="card mb-3 shadow-sm"\>  
                        \<div class\="card-body"\>  
                            \<h6 class\="card-subtitle mb-2 text-muted"\>Answer Received:\</h6\>  
                            \<div class\="alert alert-secondary pre-wrap"\>{{ sub.payload.answer }}\</div\>  
                            \<details\>  
                                \<summary\>Full Payload\</summary\>  
                                \<pre class\="small mt-2"\>{{ JSON.stringify(sub.payload, null, 2\) }}\</pre\>  
                            \</details\>  
                        \</div\>  
                    \</div\>  
                    \<div v-if\="submissions.length \=== 0" class\="text-center text-muted mt-5"\>  
                        No data yet. Run your agent against the Target URL.  
                    \</div\>  
                \</div\>  
            \</div\>  
        \</div\>  
    \</div\>  
\</div\>

\<script src\="https://cdn.jsdelivr.net/npm/vue@2/dist/vue.js"\>\</script\>  
\<script src\="https://cdn.quilljs.com/1.3.6/quill.js"\>\</script\>  
\<script\>  
    var quill \= new Quill('\#editor-container', {  
        theme: 'snow',  
        modules: {  
            toolbar: \[  
                \[{ 'header': \[1, 2, false\] }\],  
                \['bold', 'italic', 'code-block'\],  
                \['link', 'image'\],  
                \[{ 'list': 'ordered'}, { 'list': 'bullet' }, { 'script': 'sub'}, { 'script': 'super' }\]  
            \]  
        }  
    });

    new Vue({  
        el: '\#app',  
        data: {  
            submissions: \[\],  
            loading: false,  
            serverBase: window.location.origin  
        },  
        computed: {  
            quizUrl() { return this.serverBase \+ '/quiz'; }  
        },  
        methods: {  
            deployQuiz() {  
                fetch('/set\_quiz', {  
                    method: 'POST',  
                    headers: {'Content-Type': 'application/json'},  
                    body: JSON.stringify({ html: quill.root.innerHTML })  
                }).then(() \=\> alert('Quiz Live\!'));  
            },  
            generateAI() {  
                this.loading \= true;  
                fetch('/api/generate', { method: 'POST' })  
                    .then(r \=\> r.json())  
                    .then(data \=\> {  
                        if(data.error) {  
                            alert("Error: " \+ data.error);  
                        } else {  
                            // Insert generated HTML into editor  
                            quill.clipboard.dangerouslyPasteHTML(data.html);  
                        }  
                    })  
                    .catch(e \=\> alert(e))  
                    .finally(() \=\> this.loading \= false);  
            },  
            fetchSubmissions() {  
                fetch('/api/submissions').then(r \=\> r.json()).then(d \=\> this.submissions \= d);  
            }  
        },  
        mounted() {  
            setInterval(this.fetchSubmissions, 2000);  
        }  
    });  
\</script\>  
\</body\>  
\</html\>

## **5\. Usage**

1. Create a .env file in the mock-tool directory:  
   Code snippet  
   OPENAI\_API\_KEY=sk-your-api-key-here

2. Run: python mock\_server.py  
3. Open http://localhost:9000.  
4. Click **"✨ Generate Random Question"**.  
5. Review the generated question in the editor (tweak if desired).  
6. Click **"Update / Deploy Quiz Page"**.  
7. Fire your Agent at the provided URL.