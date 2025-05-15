from flask import Flask, request, render_template, redirect, url_for
from prompt import get_name_prompt, get_summary_prompt, get_items_prompt
import requests
import re
import time
import json
import os
import dbutils

app = Flask(__name__)

# Ollama server URL
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://100.112.153.1:11434/api/generate")

# Default model to use
DEFAULT_MODEL = "qwen3:30b-a3b"


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


def generate_name_and_summary(response):
    """Generate a funny name and summary using Ollama"""
    # Generate name
    name_prompt = get_name_prompt(response)
    name_payload = {
        "model": DEFAULT_MODEL,
        "stream": False,
        "prompt": name_prompt
    }
    name_response = requests.post(OLLAMA_URL, json=name_payload, stream=False)
    name = name_response.json()['response'].strip()
    name = re.sub(r'^<think>.*?</think>', '',
                  name, flags=re.DOTALL).lstrip().strip('"')

    # Generate summary
    summary_prompt = get_summary_prompt(response)
    summary_payload = {
        "model": DEFAULT_MODEL,
        "stream": False,
        "prompt": summary_prompt
    }
    summary_response = requests.post(
        OLLAMA_URL, json=summary_payload, stream=False)
    summary = summary_response.json()['response'].strip()
    summary = re.sub(r'^<think>.*?</think>', '',
                     summary, flags=re.DOTALL).lstrip().strip('"')

    return name, summary


def generate_list_items(user_input):
    payload = {
        "model": DEFAULT_MODEL,
        "stream": False,
        "prompt": get_items_prompt(user_input),
    }
    response_data = requests.post(
        OLLAMA_URL, json=payload, stream=False)
    response = response_data.json()
    response = re.sub(r'^<think>.*?</think>', '',
                      response['response'], flags=re.DOTALL).lstrip()

    items = list_to_items(response)
    return items


@app.route("/", methods=["GET", "POST"])
def index():
    # Check for cookie on GET request
    if request.method == "GET":
        last_checklist = request.cookies.get('last_checklist')
        if last_checklist:
            return redirect(url_for('view_checklist', checklist_url=last_checklist))

    response = None
    if request.method == "POST":
        user_input = request.form.get("input_text", "")
        if user_input:
            try:
                items = generate_list_items(user_input)
                # Generate name and summary
                name, summary = generate_name_and_summary(response)

                # Generate a unique URL
                url = "checklist_" + str(int(time.time()))
                dbutils.save_checklist(url, items, name, summary)
                # Set cookie and redirect
                resp = redirect(url_for('view_checklist', checklist_url=url))
                resp.set_cookie('last_checklist', url, max_age=86400, path='/')
                return resp
            except Exception as e:
                response = f"Error communicating with Ollama: {str(e)}"
    return render_template("index.html", response=response)


@app.route("/checklist/<checklist_url>", methods=["GET", "POST"])
def view_checklist(checklist_url):
    db = dbutils.get_db()
    try:
        # Fetch checklist information
        checklist = db.execute(
            "SELECT name, summary, url FROM checklist WHERE url = ?",
            (checklist_url,)
        ).fetchone()

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

        return render_template("checklist.html", items=items, checklist=checklist)
    finally:
        db.close()


@app.route("/checklist/<checklist_url>/state", methods=["GET"])
def get_checklist_state(checklist_url):
    """Endpoint to get the current state of a checklist"""
    db = dbutils.get_db()
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
                "checked": bool(row[4])  # Ensure it's a boolean
            }
            for row in items
        ]
        # Return proper JSON response with error handling
        return app.response_class(
            response=json.dumps({"items": items}, ensure_ascii=False),
            status=200,
            mimetype='application/json'
        )
    except Exception as e:
        # Return error response if something goes wrong
        return app.response_class(
            response=json.dumps({"error": str(e)}),
            status=500,
            mimetype='application/json'
        )
    finally:
        db.close()


@app.route("/reset", methods=["POST"])
def reset():
    """Handle AJAX request to reset the checklist and redirect"""
    resp = redirect(url_for('index'))
    resp.set_cookie('last_checklist', '', max_age=0, path='/')
    return resp


@app.route("/add_item", methods=["POST"])
def add_item():
    item = request.form.get("item")
    checklist_url = request.form.get("checklist_url")

    if not item or not checklist_url:
        return "Missing required parameters", 400

    # Use generate_list_items to process the item
    items = generate_list_items(item)

    db = dbutils.get_db()
    try:
        for item_data in items:
            db.execute(
                "INSERT INTO checklist_items (checklist_url, item, quantity, measurement, checked) VALUES (?, ?, ?, ?, 0)",
                (checklist_url, item_data["item"], item_data["quantity"], item_data["measurement"]),
            )
        db.commit()
        return "Item(s) added successfully", 200
    except Exception as e:
        return f"Error adding item: {str(e)}", 500
    finally:
        db.close()


if __name__ == "__main__":
    app.run(debug=True, port="3030", host="0.0.0.0")
