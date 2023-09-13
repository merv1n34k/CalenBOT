"""Contains configs for telegram bot."""

from datetime import datetime
from collections import namedtuple
from pathlib import Path
from logger import log_action as log
import fetch_schedule

# Your auth token for the bot
AUTH_TOKEN = "YOUR TOKEN"
# USER_ID of a person who control the bot
OVERLORD_USER_ID = "YOUR USER ID"
# Your schedule URL
URL = "YOUR URL"

# Bot in group settings
MAX_REQUEST = 10 # Max repeated requests for one user in REQUEST_TIME
REQUEST_TIME = 5  # in minutes

# Schedule settings
Text = namedtuple("Text", ['weekdays','timestamps','week','teacher',
                           'link','email','phone', 'no_lesson','no_day',
                           'scheduled_lesson', 'next_scheduled_lesson'])

INTERVAL = 115
START = "8:25"
END = "18:25"
WEEKDAYS = ['Понеділок', 'Вівторок', 'Середа', 'Четвер', "П'ятниця"]
TIMESTAMPS = ["08:30", "10:25", "12:20", "14:15", "16:10", "18:05"]
TEXT = Text(weekdays = WEEKDAYS,
            timestamps = TIMESTAMPS,
            week = "Тиждень",
            teacher = "Викладач",
            link = "Посилання",
            email = "Ел. Пошта",
            phone = "Телефон",
            no_lesson = "Зараз пари немає",
            no_day = "Cьогодні пар не буде",
            scheduled_lesson = "*Увага, за 5 хв розпочнеться:*\n",
            next_scheduled_lesson = "\n*Наступною парою буде:*\n",)
TABLE_IDS = ["ctl00_MainContent_SecondScheduleTable", "ctl00_MainContent_FirstScheduleTable"]
LESSON_TYPES = ["Лек","Лаб","Прак"]

# Helper functions (changing this functions is not recommended)

if not Path("./data/schedule.db").exists():
    fetch_schedule.extract_and_save_schedule(URL, TABLE_IDS, LESSON_TYPES)

def get_current_time_details(start, end, interval):
    # Get current time, day, and date
    current_time = datetime.now().time()
    current_day = datetime.now().weekday()
    current_date = datetime.now().date()

    # Determine the current week (1 for odd, 2 for even)
    current_week = 1 if current_date.isocalendar()[1] % 2 == 1 else 2

    # Determine the lesson index based on the current time and the time interval
    start_time = datetime.strptime(start, '%H:%M').time()
    end_time = datetime.strptime(end, '%H:%M').time()

    if start_time <= current_time <= end_time:
        elapsed_time = datetime.combine(datetime.today(), current_time) - datetime.combine(datetime.today(), start_time)
        lesson_index = int(elapsed_time.total_seconds() // (interval * 60))
    else:
        lesson_index = None

    return lesson_index, current_day, current_week

def form_message(msg_type,text=TEXT,link=True,info=False):
    """Return a formatted string with the info about certain lesson with given index.
    Message types: 1 - lesson info with link; 2 - list of subjects on the given day;
    3 - list of subjects for 1 week; 4 - list of subjects for whole schedule, 0 - special format
    """
    form_sch = fetch_schedule.form_schedule
    reply_text = ""
    l,d,w = get_current_time_details(START,END,INTERVAL)
    if str(msg_type) == "1":
        lesson = form_sch(text, lesson_index=l, day_index=d, week=w,
                          include_teacher_info=info, include_links=link)
        if lesson:
            reply_text += "Пара зараз:\n"
            reply_text += lesson
        else:
            reply_text += text.no_lesson
    elif str(msg_type) == "2":
        day = form_sch(text, day_index=d, week=w,
                          include_teacher_info=info, include_links=link)
        if day:
            reply_text += day
        else:
            reply_text += text.no_day
    elif str(msg_type) == "3":
        reply_text += form_sch(text, week=w,
                          include_teacher_info=info, include_links=link)
    elif str(msg_type) == "4":
        reply_text += form_sch(text,
                          include_teacher_info=info, include_links=link)
    elif str(msg_type) == "0":
        lesson = form_sch(text, lesson_index=l, day_index=d, week=w,
                          include_teacher_info=info, include_links=link)
        next_lesson = form_sch(text, lesson_index=(l+1), day_index=d, week=w, include_teacher_info=info, include_links=link)
        if not lesson:
            return text.no_lesson
        reply_text += text.scheduled_lesson
        reply_text += lesson
        if next_lesson == "":
            return reply_text
        reply_text += text.next_scheduled_lesson
        reply_text += next_lesson
    return reply_text

def fill_none_values():
    fetch_schedule.check_none_values('teachers')
    fetch_schedule.check_none_values('lessons')

