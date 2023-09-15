import requests
from bs4 import BeautifulSoup
import sqlite3
from collections import OrderedDict

conn = sqlite3.connect('data/schedule.db')
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS lessons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject TEXT,
    type TEXT,
    link TEXT,
    teacher_id INTEGER,
    FOREIGN KEY (teacher_id) REFERENCES teachers (id)
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
    FOREIGN KEY (lesson_id) REFERENCES lessons(id)
);''')

conn.close()

def check_none_values(table_name):
    conn = sqlite3.connect('data/schedule.db')
    cursor = conn.cursor()

    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()

    # Store the description in a variable before entering the loop
    description = cursor.description

    for row in rows:
        for i, field in enumerate(row[1:], start=1):
            if field is None:
                column_name = description[i][0]
                row_id = row[1]
                new_value = input(f"Enter value for {column_name} in {table_name} for {row_id}: ")
                print(new_value)
                if not new_value or new_value.strip() == "":
                    continue

                # Update the table with the new value
                cursor.execute(f"UPDATE {table_name} SET {column_name} = ? WHERE id = ?", (new_value, row_id))
    conn.close()

def extract_and_save_schedule(url, table_ids, lesson_types):
    response = requests.get(url)
    html = response.text
    soup = BeautifulSoup(html, 'html.parser')

    conn = sqlite3.connect('data/schedule.db')
    cursor = conn.cursor()

    for table_id in table_ids:
        table = soup.find('table', {'id': table_id})
        rows = table.find_all('tr')
        header = [td.text.strip() for td in rows[0].find_all('td')][1:]

        week_number = 1 if "First" in table_id else 2

        for row in rows[1:]:
            row_data = [td for td in row.find_all('td')]
            timestamp = row_data[0].text.strip()[1:]
            weekdays_data = row_data[1:]

            for i, day in enumerate(header):
                cell_content = weekdays_data[i]

                # Check if cell is empty
                if not cell_content.text.strip():
                    continue

                subject_span = cell_content.find('span', {'class': 'disLabel'})
                if subject_span:
                    subject = subject_span.text.strip()
                else:
                    continue  # Skip this cell if subject is not found

                # Extract teacher names from 'a' tags that are not inside 'span'

                teacher_elements = [a for a in cell_content.find_all('a', {'class': 'plainLink'}) if not a.find_parent('span')]
                teacher_names = [elem.text.strip() for elem in teacher_elements if all(word not in elem.text for word in lesson_types)] #

                # Extract type of lesson
                type_element = cell_content.find('a', string=lambda x: any(word in x for word in ["Лек", "Прак", "Лаб"]))
                if type_element:
                    for keyword in lesson_types:
                        if keyword in type_element.text:
                            type_of_lesson = keyword
                            break
                else:
                    # Fallback to text search if type is not in a tag
                    for keyword in lesson_types:
                        if keyword in cell_content.text:
                            type_of_lesson = keyword
                            break

                # Insert or Update teacher info
                teacher_ids = []
                for teacher_name in teacher_names:
                    cursor.execute("INSERT OR IGNORE INTO teachers (name) VALUES (?)", (teacher_name,))
                    cursor.execute("SELECT id FROM teachers WHERE name = ?", (teacher_name,))
                    teacher_ids.append(cursor.fetchone()[0])

                # Insert into lessons table
                cursor.execute("""
                    INSERT INTO lessons (subject, type, link, teacher_id)
                    VALUES (?, ?, ?, ?)
                """, (subject, type_of_lesson, None, ','.join(map(str, teacher_ids))))

                lesson_id = cursor.lastrowid  # Get the id of the last inserted row

                # Insert into schedule table
                cursor.execute("""
                    INSERT INTO schedule (timestamp, weekday, lesson_id, week_number)
                    VALUES (?, ?, ?, ?)
                """, (timestamp, day, lesson_id, week_number))

        conn.commit()

    conn.close()

def fetch_schedule_as_dict(days_order):
    # Initialize the schedule dictionary
    schedule_dict = OrderedDict()

    # Define the desired order of weekdays
    weekday_order = days_order

    # Connect to the SQLite database
    conn = sqlite3.connect('data/schedule.db')
    cursor = conn.cursor()

    # Execute query to fetch all data from the 'schedule' table
    cursor.execute("SELECT * FROM schedule")
    rows = cursor.fetchall()

    conn.close()

    # Populate the schedule dictionary
    for row in rows:
        id, timestamp, weekday, lesson_id, week_number = row

        # Initialize week if not already in the schedule
        if week_number not in schedule_dict:
            schedule_dict[week_number] = OrderedDict((day, {}) for day in weekday_order)

        # Initialize weekday if not already in the week
        if weekday not in schedule_dict[week_number]:
            schedule_dict[week_number][weekday] = {}

        # Insert the lesson into the schedule
        schedule_dict[week_number][weekday][timestamp] = lesson_id

    return schedule_dict

def fetch_lessons_as_dict():
    lessons_dict = {}

    # Connect to the SQLite database
    conn = sqlite3.connect('data/schedule.db')
    cursor = conn.cursor()

    # Execute query to fetch all data from the 'lessons' table
    cursor.execute("SELECT * FROM lessons")
    rows = cursor.fetchall()

    # Close the database connection
    conn.close()

    # Convert rows to a dictionary
    for row in rows:
        id, subject, lesson_type, link, teacher_id = row
        lessons_dict[id] = {'subject': subject, 'type': lesson_type, 'link':link, 'teacher_id': teacher_id}

    return lessons_dict

def fetch_teachers_as_dict():
    teachers_dict = {}

    # Connect to the SQLite database
    conn = sqlite3.connect('data/schedule.db')
    cursor = conn.cursor()

    # Execute query to fetch all data from the 'teachers' table
    cursor.execute("SELECT * FROM teachers")
    rows = cursor.fetchall()

    # Close the database connection
    conn.close()

    # Convert rows to a dictionary
    for row in rows:
        id, name, email, phone = row
        teachers_dict[id] = {'name': name, 'email': email, 'phone': phone}

    return teachers_dict

# Function to print schedule, using lessons dictionary to look up lesson data
def form_schedule(text, week=None, day_index=None, lesson_index=None,
                  include_teacher_info=False, include_links=True):
    schedule_dict = fetch_schedule_as_dict(text.weekdays)
    lessons_dict = fetch_lessons_as_dict()
    teachers_dict = fetch_teachers_as_dict()

    output = ""

    weekday_list = text.weekdays
    timestamp_list = text.timestamps

    for week_number, week_data in schedule_dict.items():
        if week is not None and week_number != week:
            continue

        for weekday, day_data in week_data.items():
            if day_index is not None and weekday != weekday_list[day_index]:
                continue

            output += f"*{weekday} ({text.week} {week_number}):*\n"

            for timestamp, lesson_id in day_data.items():
                if lesson_index is not None and timestamp != timestamp_list[lesson_index]:
                    continue
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
                    string = f"{text.teacher}: {teacher_name},"
                    if include_teacher_info:
                        if teacher_email:
                            string += f"\t{text.email}: {teacher_email},"
                        if teacher_phone:
                            string += f"\t{text.phone}: {teacher_phone}"
                    teacher_details.append(string)

                output += f"\t`{timestamp}: {subject} ({lesson_type})`\n"
                if include_links and lesson_link:
                    output += f"{text.link}: {lesson_link}\n"
                for detail in teacher_details:
                    output += f"\t\t\t-\t_{detail}_\n"

            output += "\n"

    return output if output else ""
