from flask import Flask, request, render_template, redirect, url_for
import sqlite3
import requests
import re
import time
import json
import os

app = Flask(__name__)

# Ollama server URL
OLLAMA_URL = "http://100.112.153.1:11434/api/chat"

# Default model to use
DEFAULT_MODEL = "qwen3:30b-a3b"


def get_db():
    """Connect to the SQLite database."""
    conn = sqlite3.connect('checklists.db')
    conn.row_factory = sqlite3.Row
    # Create tables if not exists
    conn.execute('''
        CREATE TABLE IF NOT EXISTS checklist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS checklist_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            checklist_url TEXT NOT NULL,
            item TEXT NOT NULL,
            quantity TEXT NOT NULL,
            measurement TEXT NOT NULL,
            FOREIGN KEY(checklist_url) REFERENCES checklist(url)
        )
    ''')
    return conn


def save_checklist(url, items):
    """Save a checklist to the database with individual items."""
    db = get_db()
    try:
        for item in items:
            db.execute(
                "INSERT INTO checklist_items (checklist_url, item, quantity, measurement) VALUES (?, ?, ?, ?)",
                (url, item['item'], item['quantity'], item['measurement'])
            )
        db.commit()
    except Exception as e:
        print(f"Error saving to database: {str(e)}")
    finally:
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
                                /think"
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
                response = response['message']['content'].lstrip(
                    "<think>\n\n</think>\n\n")
                items = list_to_items(response)
                print("caca", items)
                # Save to database
                # Generate a unique URL
                url = "checklist_" + str(int(time.time()))
                save_checklist(url, items)
                # Redirect to the checklist view
                return redirect(url_for('view_checklist', checklist_url=url))
            except Exception as e:
                response = f"Error communicating with Ollama: {str(e)}"
    return render_template("index.html", response=response)


@app.route("/checklist/<checklist_url>", methods=["GET", "POST"])
def view_checklist(checklist_url):
    db = get_db()
    try:
        # Fetch items from the new table
        items = db.execute(
            "SELECT item, quantity, measurement FROM checklist_items WHERE checklist_url = ?",
            (checklist_url,)
        ).fetchall()
        # Convert to list of dictionaries for template compatibility
        items = [{"item": row[0], "quantity": row[1], "measurement": row[2]} for row in items]

        # Handle checkbox updates
        if request.method == "POST":
            updated_items = []
            for i, item in enumerate(items):
                # Check if this item was checked
                checked = request.form.get(f"item_{i+1}") == 'on'
                updated_items.append({
                    "item": item["item"],
                    "quantity": item["quantity"],
                    "measurement": item["measurement"],
                    "checked": checked
                })
            # Update the database with the new check status
            db.execute("UPDATE checklist SET items = ? WHERE url = ?",
                       (json.dumps(updated_items), checklist_url))
            db.commit()
            items = updated_items

        return render_template("checklist.html", items=items)
    finally:
        db.close()


if __name__ == "__main__":
    app.run(debug=True, port="3030")
