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
    conn = sqlite3.connect('data/schedule.db')
    cursor = conn.cursor()

    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()
    description = cursor.description

    # Dictionary to keep track of rows with None values for each column
    none_values_dict = {}

    # Keep track of identical lesson rows
    ident_rows = []

    for row in rows:
        for i, field in enumerate(row[1:], start=1):  # Skip the id column
            if field is None:
                column_name = description[i][0]
                row_id = row[0]  # Assuming the id is the first column
                if table_name == "lessons":
                    subject = row[1]
                    type_ = row[2]
                    key = (subject, type_)
                    if column_name in none_values_dict and key in ident_rows:
                        none_values_dict[column_name].append(row_id)
                    else:
                        none_values_dict[column_name] = [row_id]
                        ident_rows.append(key)

                    info = f"{subject} ({type_})"
                else:
                    info = row[1]

                    if column_name in none_values_dict:
                        none_values_dict[column_name].append(row_id)
                    else:
                        none_values_dict[column_name] = [row_id]

    # Iterate through columns that have None values
    for column_name, row_ids in none_values_dict.items():
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

    conn.close()

def extract_and_save_schedule(url, table_ids, lesson_types):
    try:
        response = requests.get(url)
    except ConnectionError:
        print("Connection error, couldn't update the scedule")
        return
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
                    INSERT OR IGNORE INTO lessons (subject, type, link, teacher_id)
                    VALUES (?, ?, ?, ?)
                """, (subject, type_of_lesson, None, ','.join(map(str, teacher_ids))))

                # Get the id of the lesson that was just inserted or already existed
                cursor.execute("SELECT id FROM lessons WHERE subject = ? AND type = ? AND teacher_id = ?", (subject, type_of_lesson, ','.join(map(str, teacher_ids))))
                lesson_id = cursor.fetchone()[0]

                # Insert into schedule table
                cursor.execute("""
                    INSERT OR IGNORE INTO schedule (timestamp, weekday, lesson_id, week_number)
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
                    string = f"{text.teacher}: {teacher_name}"
                    if include_teacher_info:
                        if teacher_email:
                            string += f",\n\t{text.email}: {teacher_email}"
                        if teacher_phone:
                            string += f",\n\t{text.phone}: {teacher_phone}"
                    teacher_details.append(string)

                output += f"\t*{timestamp}:* `{subject} ({lesson_type})`\n"
                if include_links and lesson_link:
                    output += f"{text.link}: {lesson_link}\n"
                    print(lesson_link)
                for detail in teacher_details:
                    output += f"\t\t\t-\t_{detail}_\n"

            output += "\n"

    return output if output else ""
