import sqlite3


def get_db():
    """Connect to the SQLite database."""
    conn = sqlite3.connect('checklists.db')
    conn.row_factory = sqlite3.Row
    # Create tables if not exists
    conn.execute('''
        CREATE TABLE IF NOT EXISTS checklist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE,
            name TEXT,
            summary TEXT
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


def save_checklist(url, items, name, summary):
    """Save a checklist to the database with individual items."""
    db = get_db()
    try:
        # Insert into checklist table
        db.execute(
            "INSERT INTO checklist (url, name, summary) VALUES (?, ?, ?)",
            (url, name, summary)
        )

        # Insert items into checklist_items table
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
