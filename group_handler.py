
import sqlite3
from logger import log_action as log

# Constant for the database path
DB_PATH = 'data/calenbot.db'

# Initialize SQLite database and tables
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS approved_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_name TEXT UNIQUE,
    group_data TEXT
);
''')

conn.commit()

def add_group(group_name, group_data=None):
    """
    Add a new group to the approved_groups table.

    Parameters:
        group_name (str): The name of the group.
        group_data (str, optional): Additional data related to the group.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute("INSERT INTO approved_groups (group_name, group_data) VALUES (?, ?)", (group_name, group_data))
        conn.commit()
        # Replace log with your actual logging function
        log("group handler", f"Added group {group_name} to approved_groups.")
    except sqlite3.IntegrityError:
        log("group handler", "Group with this name already exists in approved_groups. No changes made.")

    conn.close()

def remove_group(group_name):
    """
    Remove a group from the approved_groups table.

    Parameters:
        group_name (str): The name of the group to be removed.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check if the group exists
    cursor.execute("SELECT COUNT(*) FROM approved_groups WHERE group_name = ?", (group_name,))
    group_exists = cursor.fetchone()[0] > 0

    if group_exists:
        cursor.execute("DELETE FROM approved_groups WHERE group_name = ?", (group_name,))
        conn.commit()
        # Replace log with your actual logging function
        log("group_handler", f"Removed group {group_name} from approved_groups.")
    else:
        log("group_handler", f"Group {group_name} does not exist in approved_groups. No changes made.")

    conn.close()

def get_groups_as_dict():
    """
    Fetch all approved groups as a dictionary.

    Returns:
        dict: A dictionary with group names as keys and group data as values.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT group_name, group_data FROM approved_groups")
    rows = cursor.fetchall()

    conn.close()

    return {group_name: group_data for group_name, group_data in rows}

