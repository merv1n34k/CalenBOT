"""
Text
"""

import sqlite3
from logger import log_action as log

# Create a new SQLite database and table
conn = sqlite3.connect('data/group_data.db')
cursor = conn.cursor()

# Create table for approved_groups
cursor.execute('''
CREATE TABLE IF NOT EXISTS approved_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_name TEXT UNIQUE,
    group_data TEXT
);
''')

# Create table for removed_data
cursor.execute('''
CREATE TABLE IF NOT EXISTS removed_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_name TEXT UNIQUE,
    group_data TEXT
);
''')

# Commit changes
conn.commit()

# Function to add a group to approved_groups
def add_new_group(group_name, group_data=None):
    try:
        cursor.execute("INSERT INTO approved_groups (group_name, group_data) VALUES (?, ?)", (group_name, group_data))
        conn.commit()
        log("group_handler", f"Added group {group_name} to approved_groups.")
    except sqlite3.IntegrityError:
        log("group_handler", "Group with this name already exists in approved_groups. No changes made.")

# Function to remove a group from approved_groups and move it to removed_data
def remove_approved_group(group_name):
    # First, fetch the data for the group to be removed
    cursor.execute("SELECT group_data FROM approved_groups WHERE group_name = ?", (group_name,))
    group_data = cursor.fetchone()

    if group_data is not None:
        # Delete the group from approved_groups
        cursor.execute("DELETE FROM approved_groups WHERE group_name = ?", (group_name,))

        # Add the group to removed_data
        try:
            cursor.execute("INSERT INTO removed_data (group_name, group_data) VALUES (?, ?)", (group_name, group_data[0]))
            log("group_handler", f"Moved group {group_name} to removed_data.")
        except sqlite3.IntegrityError:
            log("group_handler", "Group with this name already exists in removed_data. Overwriting existing entry.")
            cursor.execute("UPDATE removed_data SET group_data = ? WHERE group_name = ?", (group_data[0], group_name))

        conn.commit()
    else:
        log("group_handler", "Group not found in approved_groups. No changes made.")

# Function to get data from approved_groups as a dictionary
def get_approved_groups():
    cursor.execute("SELECT group_name, group_data FROM approved_groups")
    rows = cursor.fetchall()
    approved_groups_dict = {}
    for row in rows:
        group_name, group_data = row
        approved_groups_dict[group_name] = group_data
    return approved_groups_dict

# Close the database connection if needed
def close_connection():
    conn.close()
    log("group_handler", "Database connection closed.")
