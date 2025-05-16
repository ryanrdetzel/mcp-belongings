import datetime
import os
import sqlite3
import json
from flask import Flask, request, Response
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Define database path
DATA_DIR = os.path.join(os.getcwd(), "data")
# Create data directory if it doesn't exist
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "belongings.db")

# Initialize database
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS belongings (
        id TEXT PRIMARY KEY,
        location TEXT,
        container_name TEXT,
        contents TEXT
    )
    ''')
    conn.commit()
    conn.close()

# Initialize the database
init_db()

# SSE event functions
def format_sse(data, event=None):
    msg = f"data: {json.dumps(data)}\n\n"
    if event is not None:
        msg = f"event: {event}\n{msg}"
    return msg

@app.route('/events')
def events():
    def generate():
        yield format_sse({"message": "Connected to Belongings SSE server"})
    
    return Response(generate(), mimetype='text/event-stream')

@app.route('/add_item', methods=['POST'])
def add_item():
    data = request.json
    container_id = data.get('container_id')
    item = data.get('item')
    
    if not container_id or not item:
        return json.dumps({"error": "Missing container_id or item"}), 400
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if container exists
    cursor.execute("SELECT contents FROM belongings WHERE id = ?", (container_id,))
    result = cursor.fetchone()
    
    if result:
        contents = result[0]
        if contents:
            new_contents = contents + "," + item
        else:
            new_contents = item
        cursor.execute("UPDATE belongings SET contents = ? WHERE id = ?", (new_contents, container_id))
    else:
        cursor.execute("INSERT INTO belongings (id, contents) VALUES (?, ?)", (container_id, item))
    
    conn.commit()
    conn.close()
    return json.dumps({"message": f"Added {item} to container {container_id}"})

@app.route('/remove_item', methods=['POST'])
def remove_item():
    data = request.json
    container_id = data.get('container_id')
    item = data.get('item')
    
    if not container_id or not item:
        return json.dumps({"error": "Missing container_id or item"}), 400
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT contents FROM belongings WHERE id = ?", (container_id,))
    result = cursor.fetchone()
    
    if not result:
        conn.close()
        return json.dumps({"error": f"Container {container_id} not found"}), 404
    
    contents = result[0]
    items = contents.split(",")
    
    if item in items:
        items.remove(item)
        new_contents = ",".join(items)
        cursor.execute("UPDATE belongings SET contents = ? WHERE id = ?", (new_contents, container_id))
        conn.commit()
        conn.close()
        return json.dumps({"message": f"Removed {item} from container {container_id}"})
    else:
        conn.close()
        return json.dumps({"error": f"Item {item} not found in container {container_id}"}), 404

@app.route('/move_item', methods=['POST'])
def move_item():
    data = request.json
    from_container_id = data.get('from_container_id')
    to_container_id = data.get('to_container_id')
    item = data.get('item')
    
    if not from_container_id or not to_container_id or not item:
        return json.dumps({"error": "Missing from_container_id, to_container_id, or item"}), 400
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if source container exists and has the item
    cursor.execute("SELECT contents FROM belongings WHERE id = ?", (from_container_id,))
    result = cursor.fetchone()
    
    if not result:
        conn.close()
        return json.dumps({"error": f"Container {from_container_id} not found"}), 404
    
    contents = result[0]
    items = contents.split(",")
    
    if item not in items:
        conn.close()
        return json.dumps({"error": f"Item {item} not found in container {from_container_id}"}), 404
    
    # Remove from source container
    items.remove(item)
    new_contents = ",".join(items)
    cursor.execute("UPDATE belongings SET contents = ? WHERE id = ?", (new_contents, from_container_id))
    
    # Add to destination container
    cursor.execute("SELECT contents FROM belongings WHERE id = ?", (to_container_id,))
    result = cursor.fetchone()
    
    if result:
        contents = result[0]
        if contents:
            new_contents = contents + "," + item
        else:
            new_contents = item
        cursor.execute("UPDATE belongings SET contents = ? WHERE id = ?", (new_contents, to_container_id))
    else:
        cursor.execute("INSERT INTO belongings (id, contents) VALUES (?, ?)", (to_container_id, item))
    
    conn.commit()
    conn.close()
    return json.dumps({"message": f"Moved {item} from {from_container_id} to {to_container_id}"})

@app.route('/search_item', methods=['GET'])
def search_item():
    item = request.args.get('item')
    
    if not item:
        return json.dumps({"error": "Missing item parameter"}), 400
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, contents FROM belongings")
    results = cursor.fetchall()
    
    found_in = []
    for container_id, contents in results:
        if contents and item in contents.split(","):
            found_in.append(container_id)
    
    conn.close()
    
    if found_in:
        return json.dumps({"message": f"Item {item} found in containers", "containers": found_in})
    else:
        return json.dumps({"message": f"Item {item} not found in any container"})

@app.route('/get_all_items', methods=['GET'])
def get_all_items():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, location, container_name, contents FROM belongings")
    results = cursor.fetchall()
    
    all_items = []
    for container_id, location, container_name, contents in results:
        container = {
            "id": container_id,
            "location": location,
            "name": container_name,
            "contents": contents.split(",") if contents else []
        }
        all_items.append(container)
    
    conn.close()
    return json.dumps({"containers": all_items})

@app.route('/update_container_info', methods=['POST'])
def update_container_info():
    data = request.json
    container_id = data.get('container_id')
    location = data.get('location')
    container_name = data.get('container_name')
    
    if not container_id:
        return json.dumps({"error": "Missing container_id"}), 400
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM belongings WHERE id = ?", (container_id,))
    if not cursor.fetchone():
        conn.close()
        return json.dumps({"error": f"Container {container_id} not found"}), 404
    
    updates = []
    params = []
    
    if location is not None:
        updates.append("location = ?")
        params.append(location)
    
    if container_name is not None:
        updates.append("container_name = ?")
        params.append(container_name)
    
    if updates:
        query = f"UPDATE belongings SET {', '.join(updates)} WHERE id = ?"
        params.append(container_id)
        cursor.execute(query, params)
        conn.commit()
        conn.close()
        return json.dumps({"message": f"Updated container {container_id} information"})
    else:
        conn.close()
        return json.dumps({"error": "No updates provided"}), 400

if __name__ == "__main__":
    app.run(debug=True, port=5000)
