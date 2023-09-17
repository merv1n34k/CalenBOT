import requests
from bs4 import BeautifulSoup
import sqlite3
from collections import OrderedDict

DB_PATH = 'data/calenbot.db'
# Constants for table indices
ID_INDEX = 0
SUBJECT_INDEX = 1
TYPE_INDEX = 2
LINK_INDEX = 3
TEACHER_ID_INDEX = 4
TIMESTAMP_INDEX = 1
WEEKDAY_INDEX = 2
WEEK_NUMBER_INDEX = 4


conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS lessons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject TEXT,
    type TEXT,
    link TEXT,
    teacher_id TEXT,
    FOREIGN KEY (teacher_id) REFERENCES teachers (id),
    UNIQUE(subject, type, teacher_id)
);''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS teachers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE,
    email TEXT,
    phone TEXT
);''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS schedule (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    weekday TEXT,
    lesson_id INTEGER,
    week_number INTEGER,
    FOREIGN KEY (lesson_id) REFERENCES lessons(id),
    UNIQUE(timestamp, weekday, lesson_id, week_number)
);''')

conn.close()


def check_none_values(table_name):
    """
    Checks for None values in a SQLite table and prompts the user to fill them.

    Parameters:
        table_name (str): Name of the table to check.

    Returns:
        None
    """
    # Initialize SQLite connection
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Fetch all rows from the table
    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()
    description = cursor.description

    # Dictionary to track rows with None values
    none_values_dict = {}

    # Iterate through rows to find None values
    for row in rows:
        for i, field in enumerate(row[1:], start=1):  # Skip the 'id' column
            if field is None:
                column_name = description[i][0]
                row_id = row[ID_INDEX]

                # Create a unique key based on table type
                if table_name == "lessons":
                    subject = row[SUBJECT_INDEX]
                    type_ = row[TYPE_INDEX]
                    info = f"{subject} ({type_})"
                    key = (subject, type_)
                else:
                    key = row[SUBJECT_INDEX]  # Assuming the second column is unique in other tables
                    info = key

                # Initialize dictionary for a new unique key
                if key not in none_values_dict:
                    none_values_dict[key] = {'info': info, 'columns': {}}

                # Initialize list for a new column with None values
                if column_name not in none_values_dict[key]['columns']:
                    none_values_dict[key]['columns'][column_name] = []

                # Add row ID to the corresponding column
                none_values_dict[key]['columns'][column_name].append(row_id)

    # Prompt the user to fill None values and update the table
    for key, details in none_values_dict.items():
        info = details['info']
        for column_name, row_ids in details['columns'].items():
            new_value = input(f"Enter value for {column_name} in {table_name} for {info}: ")

            if not new_value or new_value.strip() == "":
                continue

            for row_id in row_ids:
                cursor.execute(
                    f"UPDATE {table_name} SET {column_name} = ? WHERE id = ?",
                    (new_value, row_id)
                )

            # Commit changes to the database
            conn.commit()

    # Close the SQLite connection
    conn.close()

def extract_and_save_schedule(url, table_ids, lesson_types):
    """
    Extracts schedule information from a URL and saves it to an SQLite database.

    Parameters:
        url (str): The URL to scrape.
        table_ids (list): List of table IDs to look for in the HTML.
        lesson_types (list): List of lesson types to consider.

    Returns:
        None
    """
    try:
        response = requests.get(url)
    except ConnectionError:
        print("Connection error, couldn't update the schedule")
        return

    html = response.text
    soup = BeautifulSoup(html, 'html.parser')

    # Initialize SQLite connection
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Iterate through each table ID
    for table_id in table_ids:
        table = soup.find('table', {'id': table_id})
        rows = table.find_all('tr')
        header = [td.text.strip() for td in rows[0].find_all('td')][1:]
        week_number = 1 if "First" in table_id else 2

        # Iterate through each row in the table
        for row in rows[1:]:
            row_data = [td for td in row.find_all('td')]
            timestamp = row_data[0].text.strip()[1:]
            weekdays_data = row_data[1:]

            # Iterate through each weekday
            for i, day in enumerate(header):
                cell_content = weekdays_data[i]

                # Skip empty cells
                if not cell_content.text.strip():
                    continue

                # Extract and validate subject
                subject_span = cell_content.find('span', {'class': 'disLabel'})
                if subject_span:
                    subject = subject_span.text.strip()
                else:
                    continue  # Skip if subject is not found

                # Extract teacher names
                teacher_elements = [a for a in cell_content.find_all('a', {'class': 'plainLink'}) if not a.find_parent('span')]
                teacher_names = [elem.text.strip() for elem in teacher_elements if all(word not in elem.text for word in lesson_types)]

                # Extract and validate type of lesson
                type_element = cell_content.find('a', string=lambda x: any(word in x for word in lesson_types))
                if type_element:
                    type_of_lesson = next((keyword for keyword in lesson_types if keyword in type_element.text), None)
                else:
                    type_of_lesson = next((keyword for keyword in lesson_types if keyword in cell_content.text), None)

                # Insert or update teacher information
                teacher_ids = []
                for teacher_name in teacher_names:
                    cursor.execute("INSERT OR IGNORE INTO teachers (name) VALUES (?)", (teacher_name,))
                    cursor.execute("SELECT id FROM teachers WHERE name = ?", (teacher_name,))
                    teacher_ids.append(cursor.fetchone()[ID_INDEX])

                # Insert or ignore lesson information
                cursor.execute("""
                    INSERT OR IGNORE INTO lessons (subject, type, link, teacher_id)
                    VALUES (?, ?, ?, ?)
                """, (subject, type_of_lesson, None, ','.join(map(str, teacher_ids))))

                # Retrieve the lesson ID
                cursor.execute("SELECT id FROM lessons WHERE subject = ? AND type = ? AND teacher_id = ?",
                               (subject, type_of_lesson, ','.join(map(str, teacher_ids))))
                lesson_id = cursor.fetchone()[ID_INDEX]

                # Insert or ignore schedule information
                cursor.execute("""
                    INSERT OR IGNORE INTO schedule (timestamp, weekday, lesson_id, week_number)
                    VALUES (?, ?, ?, ?)
                """, (timestamp, day, lesson_id, week_number))

        # Commit changes to the database
        conn.commit()

    # Close SQLite connection
    conn.close()

def fetch_data_as_dict(table_name, key_index=ID_INDEX):
    """
    Fetches all rows from an SQLite table and converts them to a dictionary.

    Parameters:
        table_name (str): The name of the table to fetch from.
        key_index (int): The index of the column to use as the dictionary key.

    Returns:
        dict: The fetched data in dictionary form.
    """
    data_dict = {}
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()
    description = cursor.description  # This will contain column names
    conn.close()

    column_names = [column[0] for column in description]

    for row in rows:
        key = row[key_index]
        # Create a dictionary for each row
        row_dict = {column_names[i]: value for i, value in enumerate(row)}
        data_dict[key] = row_dict

    return data_dict

def fetch_schedule_as_dict(days_order):
    """
    Fetches the schedule from the SQLite database and returns it as an ordered dictionary.

    Parameters:
        days_order (list): The desired order of weekdays.

    Returns:
        OrderedDict: The schedule data, organized by week number and weekday.
    """
    schedule_dict = OrderedDict()
    weekday_order = days_order
    schedule_data = fetch_data_as_dict('schedule')

    for _, row_dict in schedule_data.items():
        timestamp = row_dict['timestamp']
        weekday = row_dict['weekday']
        lesson_id = row_dict['lesson_id']
        week_number = row_dict['week_number']

        if week_number not in schedule_dict:
            schedule_dict[week_number] = OrderedDict((day, {}) for day in weekday_order)

        if weekday not in schedule_dict[week_number]:
            schedule_dict[week_number][weekday] = {}

        schedule_dict[week_number][weekday][timestamp] = lesson_id

    return schedule_dict

def form_schedule(text, week=None, day_index=None, lesson_index=None,
                  include_teacher_info=False, include_links=True):
    """
    Formats the schedule data as a string, optionally filtering by week, day, and lesson index.

    Parameters:
        text (object): An object containing text templates and other contextual information.
        week (int, optional): The week number to filter by.
        day_index (int, optional): The index of the day to filter by.
        lesson_index (int, optional): The index of the lesson to filter by.
        include_teacher_info (bool, optional): Whether to include teacher contact information.
        include_links (bool, optional): Whether to include lesson links.

    Returns:
        str: The formatted schedule data.
    """
    schedule_dict = fetch_schedule_as_dict(text.weekdays)
    lessons_dict = fetch_data_as_dict('lessons')
    teachers_dict = fetch_data_as_dict('teachers')

    output = ""
    weekday_list = text.weekdays
    timestamp_list = text.timestamps

    for week_number, week_data in schedule_dict.items():
        if week is not None and week_number != week:
            continue

        for weekday, day_data in week_data.items():
            if day_index is not None:
                if day_index in range(5):
                    if weekday != weekday_list[day_index]:
                        continue
                else:
                    return ""

            output += f"*{weekday} ({text.week} {week_number}):*\n"

            for timestamp, lesson_id in day_data.items():
                if lesson_index is not None:
                    if lesson_index in range(6):
                        if timestamp != timestamp_list[lesson_index]:
                            continue
                    else:
                        return ""
                lesson_data = lessons_dict.get(lesson_id, {})
                subject = lesson_data.get('subject', 'N/A')
                lesson_type = lesson_data.get('type', 'N/A')
                lesson_link = lesson_data.get('link', 'N/A')

                teacher_ids_str = lesson_data.get('teacher_id', '')
                try:
                    teacher_ids = teacher_ids_str.split(",") if teacher_ids_str else []
                except AttributeError:
                    teacher_ids = [teacher_ids_str]

                teacher_details = []
                for teacher_id in teacher_ids:
                    teacher_data = teachers_dict.get(int(teacher_id), {})
                    teacher_name = teacher_data.get('name', 'N/A')
                    teacher_email = teacher_data.get('email', 'N/A')
                    teacher_phone = teacher_data.get('phone', 'N/A')
                    string = f"{text.teacher}: {teacher_name}"
                    if include_teacher_info:
                        if teacher_email:
                            string += f",\n\t{text.email}: {teacher_email}"
                        if teacher_phone:
                            string += f",\n\t{text.phone}: {teacher_phone}"
                    teacher_details.append(string)

                output += f"\t*{timestamp}:* `{subject} ({lesson_type})`\n"
                if include_links and lesson_link:
                    output += f"\t\t\t-\t*{text.link}:* {lesson_link}\n"
                for detail in teacher_details:
                    output += f"\t\t\t-\t_{detail}_\n"

            output += "\n"

    return output if output else ""
