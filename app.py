from flask import Flask, request, render_template
import sqlite3
import requests
import re
import time
import json

app = Flask(__name__)

# Ollama server URL
OLLAMA_URL = "http://100.112.153.1:11434/api/chat"

# Default model to use
DEFAULT_MODEL = "qwen3:30b-a3b"


def get_db():
    """Connect to the SQLite database."""
    conn = sqlite3.connect('checklists.db')
    conn.row_factory = sqlite3.Row
    return conn

def save_checklist(url, items):
    """Save a checklist to the database."""
    db = get_db()
    db.execute("INSERT INTO checklist (url, items) VALUES (?, ?)", 
              (url, json.dumps(items)))
    db.commit()
    db.close()

def list_to_items(input_str):
    pattern = r'(\w+)\s+x\s+(\d+)(\w*)'

    result = []
    for match in re.finditer(pattern, input_str):
        item = match.group(1)
        quantity = match.group(2)
        measurement = match.group(3)
        if not measurement:
            measurement = "buc"
        result.append({
            "item": item,
            "quantity": quantity,
            "measurement": measurement
        })
    return result


@app.route("/", methods=["GET", "POST"])
def index():
    response = None
    if request.method == "POST":
        user_input = request.form.get("input_text", "")
        if user_input:
            try:
                # Send request to Ollama
                payload = {
                    "model": DEFAULT_MODEL,
                    "stream": False,
                    "messages": [
                        {
                            "role": "user",
                            "content": """
                                You are a helpful shopping list assistant. You are here to transform long lists of text into a nice shopping list. 
                                First think hard into which category does each item in the input list belong to, then group them by category aisle and then output a sorted list by category aisle.
                                For example: `ceapa cola castraveti hartie igienica pizza apa` 
                                you will transform into:  `hartie igienica, apa, cola, ceapa, castraveti, pizza`.
                                Another example: `doua cepe, doua cola, trei mere` transform into: `ceapa x 2, mere x 3, cola x 2`.
                                Another example: `un bax de sprite, doua kilograme de ceapa, doua cola, 2 litrii de lapte` transform into: `ceapa x 2kg, cola x 2, sprite x 1bax, lapte x 2l`.
                                Another example: `trei sticle la doi litrii de cola si doua kilograme de castraveti` transform into: `cola (2l) x 3, castraveti x 2kg`.
                                Only output the final list.
                                /no-think"
                            """
                        },
                        {
                            "role": "user",
                            "content": "This is the input: `" + user_input + "`"
                        }
                    ]
                }
                response_data = requests.post(
                    OLLAMA_URL, json=payload, stream=False)
                response = response_data.json()
                print(response)
                response = response['message']['content'].lstrip(
                    "<think>\n\n</think>\n\n")
                items = list_to_items(response)
                # Save to database
                url = "checklist_" + str(int(time.time()))  # Generate a unique URL
                save_checklist(url, items)
            except Exception as e:
                response = f"Error communicating with Ollama: {str(e)}"
    return render_template("index.html", response=response)


@app.route("/checklist/<checklist_url>")
def view_checklist(checklist_url):
    db = get_db()
    row = db.execute("SELECT items FROM checklist WHERE url = ?", (checklist_url,)).fetchone()
    db.close()

    if not row:
        return "Checklist not found", 404

    items = json.loads(row[0])
    return render_template("checklist.html", items=items)


if __name__ == "__main__":
    app.run(debug=True, port="3030")
