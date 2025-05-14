from flask import Flask, request, render_template, redirect, url_for
import sqlite3
import requests
import re
import time
import json
import os

app = Flask(__name__)

# Ollama server URL
OLLAMA_URL = "http://100.112.153.1:11434/api/generate"

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
            checked BOOLEAN NOT NULL DEFAULT 0,
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
    items = [item.strip() for item in input_str.split(',')]
    result = []

    for item in items:
        if 'x' in item:
            item_part, quantity_part = item.split('x', 1)
            item_name = item_part.strip()
            quantity_part = quantity_part.strip()

            # Use regex to extract quantity and measurement from the quantity part
            match = re.match(r'(\d+)(\w*)', quantity_part)
            if match:
                quantity = match.group(1)
                measurement = match.group(2) or 'buc'
                result.append({
                    'item': item_name,
                    'quantity': quantity,
                    'measurement': measurement
                })
        else:
            # No 'x' found, assume quantity is 1 and measurement is 'buc'
            result.append({
                'item': item.strip(),
                'quantity': '1',
                'measurement': 'buc'
            })

    return result


@app.route("/", methods=["GET", "POST"])
def index():
    # Check for cookie on GET request
    if request.method == "GET":
        last_checklist = request.cookies.get('last_checklist')
        if last_checklist:
            return redirect(url_for('view_checklist', checklist_url=last_checklist))

    response = None
    if request.method == "POST":
        # Check if the reset cookie flag is present
        if 'reset_cookie' in request.form:
            # Delete the cookie and redirect to index
            resp = redirect(url_for('index'))
            resp.set_cookie('last_checklist', '', max_age=0, path='/')
            return resp

        user_input = request.form.get("input_text", "")
        if user_input:
            try:
                # Send request to Ollama
                payload = {
                    "model": DEFAULT_MODEL,
                    "stream": False,
                    "prompt": """
                                You are a helpful shopping list assistant. Your task is to transform raw user input into a clean, organized shopping list. Follow these strict rules:

                                1. **Categorization & Sorting**
                                   - Group items by category (e.g., produce, dairy, household)
                                   - Sort categories alphabetically
                                   - Sort items within each category alphabetically

                                2. **Formatting Rules**
                                   - Use the format: `item x quantity [measurement]` (e.g., "apple x 2", "milk x 1l")
                                   - Omit "x" if quantity is 1 (e.g., "apple", "milk")
                                   - Use standard abbreviations: 
                                     - kg = kilograms
                                     - g = grams
                                     - l = liters
                                   - For complex quantities: 
                                     - "2 liters of milk" → "milk x 2l"
                                     - "a box of cereal" → "cereal x 1"
                                     - "three 2-liter bottles of soda" → "soda (2l) x 3"

                                3. **Examples**
                                   - Input: "ceapa cola castraveti hartie igienica pizza apa"
                                     → Output: "hartie igienica, apa, cola, ceapa, castraveti, pizza"
                                   - Input: "doua cepe, doua cola, trei mere"
                                     → Output: "ceapa x 2, cola x 2, mere x 3"
                                   - Input: "un bax de sprite, doua kilograme de ceapa, doua cola, 2 litrii de lapte"
                                     → Output: "ceapa x 2kg, cola x 2, sprite x 1bax, lapte x 2l"
                                   - Input: "trei sticle la doi litrii de cola si doua kilograme de castraveti"
                                     → Output: "cola (2l) x 3, castraveti x 2kg"
                                   - Input: "5kg of apples, 3 bottles of water, 2kg of potatoes"
                                     → Output: "apples x 5kg, potatoes x 2kg, water x 3"

                                4. **Do Not Include**
                                   - Any explanations or extra text
                                   - Redundant information
                                   - Unnecessary details about quantities
                                   - Non-shopping items (e.g., "please buy")

                                Only output the final list. Do not add any additional text or formatting.
                            """ + "This is the input you need to transform: `" + user_input + "` /no-think"
                }
                response_data = requests.post(
                    OLLAMA_URL, json=payload, stream=False)
                response = response_data.json()
                response = re.sub(r'^<think>.*?</think>', '',
                                  response['response'], flags=re.DOTALL).lstrip()

                print("og", response)
                items = list_to_items(response)
                print("caca", items)
                # Save to database
                # Generate a unique URL
                url = "checklist_" + str(int(time.time()))
                save_checklist(url, items, name, summary)
                # Set cookie and redirect
                resp = redirect(url_for('view_checklist', checklist_url=url))
                resp.set_cookie('last_checklist', url, max_age=86400, path='/')
                return resp
            except Exception as e:
                response = f"Error communicating with Ollama: {str(e)}"
    return render_template("index.html", response=response)


@app.route("/checklist/<checklist_url>", methods=["GET", "POST"])
def view_checklist(checklist_url):
    db = get_db()
    try:
        # Fetch items from the new table
        items = db.execute(
            "SELECT id, item, quantity, measurement, checked FROM checklist_items WHERE checklist_url = ?",
            (checklist_url,)
        ).fetchall()
        # Convert to list of dictionaries for template compatibility
        items = [
            {
                "id": row[0],
                "item": row[1],
                "quantity": row[2],
                "measurement": row[3],
                "checked": row[4]
            }
            for row in items
        ]

        # Handle checkbox updates
        if request.method == "POST":
            for item in items:
                item_id = item['id']
                checked = request.form.get(f"item_{item_id}") == 'on'
                db.execute(
                    "UPDATE checklist_items SET checked = ? WHERE id = ?",
                    (int(checked), item_id)
                )
            db.commit()

        return render_template("checklist.html", items=items)
    finally:
        db.close()


if __name__ == "__main__":
    app.run(debug=True, port="3030")
def generate_name_and_summary(response):
    # Generate a funny name (movie or food themed) with the current date
    name = f"Shopping List {time.strftime('%Y-%m-%d')}"
    
    # Create a short summary of the checklist
    items = [item['item'] for item in list_to_items(response)]
    summary = ", ".join(items[:5]) + ("..." if len(items) > 5 else "")
    
    return name, summary
