import datetime
import os
import sqlite3

from fastmcp import FastMCP

mcp = FastMCP(
    name="Belongings",
    instructions="Track items in containers across various locations. Use commands to search, add, remove, and move items between containers.",
)

# Define database path
DATA_DIR = os.path.join(os.getcwd(), "data")
# Create data directory if it doesn't exist
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "belongings.db")


# Initialize database
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS belongings (
        id TEXT PRIMARY KEY,
        location TEXT,
        container_name TEXT,
        contents TEXT
    )
    """
    )
    conn.commit()
    conn.close()


# Initialize the database
init_db()


@mcp.tool
def add_item(container_id: str, item: str):
    """Add an item to a container. If the container doesn't exist, create it."""
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
        cursor.execute(
            "UPDATE belongings SET contents = ? WHERE id = ?",
            (new_contents, container_id),
        )
    else:
        cursor.execute(
            "INSERT INTO belongings (id, contents) VALUES (?, ?)", (container_id, item)
        )

    conn.commit()
    conn.close()
    return f"Added {item} to container {container_id}"


@mcp.tool
def remove_item(container_id: str, item: str):
    """Remove an item from a container."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT contents FROM belongings WHERE id = ?", (container_id,))
    result = cursor.fetchone()

    if not result:
        conn.close()
        return f"Container {container_id} not found"

    contents = result[0]
    items = contents.split(",")

    if item in items:
        items.remove(item)
        new_contents = ",".join(items)
        cursor.execute(
            "UPDATE belongings SET contents = ? WHERE id = ?",
            (new_contents, container_id),
        )
        conn.commit()
        conn.close()
        return f"Removed {item} from container {container_id}"
    else:
        conn.close()
        return f"Item {item} not found in container {container_id}"


@mcp.tool
def move_item(from_container_id: str, to_container_id: str, item: str):
    """Move an item from one container to another."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check if source container exists and has the item
    cursor.execute("SELECT contents FROM belongings WHERE id = ?", (from_container_id,))
    result = cursor.fetchone()

    if not result:
        conn.close()
        return f"Container {from_container_id} not found"

    contents = result[0]
    items = contents.split(",")

    if item not in items:
        conn.close()
        return f"Item {item} not found in container {from_container_id}"

    # Remove from source container
    items.remove(item)
    new_contents = ",".join(items)
    cursor.execute(
        "UPDATE belongings SET contents = ? WHERE id = ?",
        (new_contents, from_container_id),
    )

    # Add to destination container
    cursor.execute("SELECT contents FROM belongings WHERE id = ?", (to_container_id,))
    result = cursor.fetchone()

    if result:
        contents = result[0]
        if contents:
            new_contents = contents + "," + item
        else:
            new_contents = item
        cursor.execute(
            "UPDATE belongings SET contents = ? WHERE id = ?",
            (new_contents, to_container_id),
        )
    else:
        cursor.execute(
            "INSERT INTO belongings (id, contents) VALUES (?, ?)",
            (to_container_id, item),
        )

    conn.commit()
    conn.close()
    return f"Moved {item} from {from_container_id} to {to_container_id}"


@mcp.tool
def search_item(item: str):
    """Search for an item across all containers."""
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
        return f"Item {item} found in containers: {', '.join(found_in)}"
    else:
        return f"Item {item} not found in any container"


@mcp.tool
def get_all_items():
    """Get all items from all containers for LLM processing."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT id, location, container_name, contents FROM belongings")
    results = cursor.fetchall()

    all_items = []
    for container_id, location, container_name, contents in results:
        if contents:
            container_info = f"Container ID: {container_id}"
            if location:
                container_info += f", Location: {location}"
            if container_name:
                container_info += f", Name: {container_name}"
            container_info += f" contains: {contents}"
            all_items.append(container_info)

    conn.close()
    return "\n".join(all_items)


@mcp.tool
def update_container_info(
    container_id: str, location: str = None, container_name: str = None
):
    """Update container location or name."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM belongings WHERE id = ?", (container_id,))
    if not cursor.fetchone():
        conn.close()
        return f"Container {container_id} not found"

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
        return f"Updated container {container_id} information"
    else:
        conn.close()
        return "No updates provided"


if __name__ == "__main__":
    mcp.run(transport="sse", host="0.0.0.0", port=8002)
