"""Contains configs for telegram bot."""

from datetime import datetime
from collections import namedtuple
import fetch_schedule

# Your auth token for the bot
AUTH_TOKEN = "YOUR TOKEN"
# USER_ID of a person who control the bot
OVERLORD_USER_ID = "YOUR ID"
# Your schedule URL
URL = ""

# Bot in group settings
MAX_REQUEST = 3 # Max repeated requests for one user in REQUEST_TIME
REQUEST_TIME = 1  # in minutes

# Schedule settings
Text = namedtuple("Text", ['weekdays','timestamps','week','teacher',
                           'link','email','phone', 'no_lesson','no_day',
                           'scheduled_lesson', 'next_lesson','current_lesson','err',
                           'unknown_command','no_auth','verbose_mode','deaf_mode',
                           'request_limit'])

INTERVAL = 115 * 60 # In minutes
START = "8:25"
END = "18:25"
LESSON_LENGTH = 95 * 60 # In minutes
AUTODELETE = 3 * 60 # In minutes
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
            current_lesson = "*Зараз йде/буде пара:*\n",
            next_lesson = "\n*Наступною парою буде:*\n",
            err = "Помилка у розкладі, дані відсутні!",
            unknown_command = "Вибач, цю команду я не знаю(",
            no_auth = "You're not authorized to use this bot!",
            request_limit = "Ліміт запросів перевищеноб будь ласка почекайте!",
            verbose_mode = ["Додаткова інфа до розладу:",'Викл.','Вкл.'],
            deaf_mode = ["Чи реагую на команди?",'Так!','Ні!'],
)
TABLE_IDS = ["ctl00_MainContent_SecondScheduleTable", "ctl00_MainContent_FirstScheduleTable"]
LESSON_TYPES = ["Лек","Лаб","Прак"]

# Helper functions (changing this functions is not recommended)

fetch_schedule.extract_and_save_schedule(URL, TABLE_IDS, LESSON_TYPES)

def get_current_time_details(start, end, interval, lesson_length):
    """
    Get details about the current time, day, and week.

    Parameters:
        start (str): The start time in HH:MM format.
        end (str): The end time in HH:MM format.
        interval (int): The interval between lessons in seconds.
        lesson_length (int): The interval between lessons end and next lesson start in seconds.

    Returns:
        tuple: The current lesson index, day of the week, and week number (odd/even).
    """
    current_time = datetime.now().time()
    current_day = datetime.now().weekday()
    current_date = datetime.now().date()
    current_week = 2 if current_date.isocalendar()[1] % 2 == 1 else 1

    start_time = datetime.strptime(start, '%H:%M').time()
    end_time = datetime.strptime(end, '%H:%M').time()

    if start_time <= current_time <= end_time:
        elapsed_time = datetime.combine(datetime.today(), current_time) - datetime.combine(datetime.today(), start_time)
        total_seconds = elapsed_time.total_seconds()
        lesson_index = int(total_seconds // (interval))

    # Check if we are exactly at the end of a lesson
        if total_seconds % (interval) == 0:
            lesson_index += 1  # Move to the next lesson index

    # Check if we are between lessons
        elif total_seconds % (interval) <= (lesson_length):
            lesson_index += 1  # Move to the next lesson index
    else:
        lesson_index = 100 # To make sure the lesson_index is out of range

    return lesson_index, current_day, current_week

def form_message(msg_type, text=TEXT, link=True, info=False, return_false=False, callback_message=False):
    """
    Generate a message based on the type specified.

    Parameters:
        msg_type (str): Type of message to generate.
        text (object): Text object containing various text templates.
        link (bool): Whether to include links in the message.
        info (bool): Whether to include additional information.
        return_false (bool): Whether to return False if date out of schedule range.
        callback_message (bool): Changes the text of the message for MESSAGE_NOW

    Returns:
        str: The generated message.
    """
    MESSAGE_NOW = 0
    MESSAGE_TODAY = 1
    MESSAGE_WEEK = 2
    MESSAGE_ALL = 3

    form_sch = fetch_schedule.form_schedule
    reply_text = ""
    l, d, w = get_current_time_details(START, END, INTERVAL,LESSON_LENGTH)

    if msg_type == MESSAGE_NOW:
        lesson = form_sch(text, lesson_index=l, day_index=d, week=w, include_teacher_info=info, include_links=link)
        next_lesson = form_sch(text, lesson_index=(l+1), day_index=d, week=w, include_teacher_info=info, include_links=link)
        current_lesson_text = text.scheduled_lesson if callback_message else text.current_lesson
        reply_text += current_lesson_text if lesson else text.no_lesson
        reply_text += lesson
        reply_text += text.next_scheduled_lesson + next_lesson if next_lesson else ""
        if return_false and reply_text == text.no_lesson:
            return False
    elif msg_type == MESSAGE_TODAY:
        day = form_sch(text, day_index=d, week=w, include_teacher_info=info, include_links=link)
        reply_text += day if day else text.no_day
    elif msg_type == MESSAGE_WEEK:
        week = form_sch(text, week=w, include_teacher_info=info, include_links=link)
        reply_text += week if week else text.err
    elif msg_type == MESSAGE_ALL:
        week_1 = form_sch(text, week=1, include_teacher_info=info, include_links=link)
        week_2 = form_sch(text, week=2, include_teacher_info=info, include_links=link)
        all = week_1 + "%%" + week_2
        reply_text += all if all else text.err

    return reply_text

def fill_none_values():
    fetch_schedule.check_none_values('teachers')
    fetch_schedule.check_none_values('lessons')


def get_welcome_message():

    # Fill in the placeholders with actual information
    bot_name='CalenBOT'
    description='~поработити людство~ надсилати вам розклад швидко та у зручній формі 😉'
    pros='\- *Багатогранний:* Можу відправляти розклад будь\-якої групи\n\- *Дбайливий:* Попереджаю за 5хв про початок пари з посиланням\n\- *Тренований:* Можу відправити розклад на зараз, на день, тиждень та загальний якщо попросите, та маю ліміт на запроси, щоб не було спаму\n\- *Відкритий:* Мій код у відкритому доступі 😉\n\- *Слухняний:* Адміни групи можуть мене контролювати\n\- *Обережний:* інші групи не можуть мене використовувати без дозволу\n\- *Чистоплотний:* автоматично видаляю кожні 3хв старі команди та свої повідомлення, щоб тримати чат у чистоті'
    cons='\- Не можу працювати у персональних чатах\n\- Не зможу провести психологічний сеанс після пари з біохімії\n\- Наразі можу працювати періодично, адже залежу від того, хто запускає бота\n\- На даний момент не можу зробити зміни в розкладі про перенесення пар\n\- Поки що працюю лише з постійними посиланнями та з одним посиланням на одну пару'
    how_to_use = "1\. Я можу автоматично надсилати повідомлення про початок пари з посиланням\. Цю опцію запускають лише адміни групи, та _володар бота_\n2\. Якщо потрібно дізнатись розклад в інший час то після натискання `/` ви можете побачити 4 команди, які я можу виконати\. Адміни мають більше команд\.\n3\. *That's all, let's go\!*\n\n"
    author_name='Oleksii Stroganov'
    github_repo='https://github\.com/merv1n34k/CalenBOT'

    # Template for the welcome message
    welcome_message = (
        f"*Вітаю\!*\n\nЯ _{bot_name}_\. Моя мета це {description}\.\n\n"

        "*Не знаєш чи я тобі потрібен?\nТоді трохи інфи про мене:\n\n*"
        "🦾*Мої переваги:*\n"
        f"{pros}\n\n"
        "🤕*Мої недоліки:*\n"
        f"{cons}\n\n"

        "❓*Як зі мною працювати:*\n"
        f"{how_to_use}"

        "*Трохи про бацька:*\n"
        f"_Автор:_ {author_name}\n"
        f"_Де я живу:_ {github_repo}\n"
    )

    return welcome_message

# Example usage
if __name__ == "__main__":
    print(get_welcome_message())

