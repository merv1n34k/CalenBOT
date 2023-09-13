"""This is the core of the bot. It launches the app,
maintain handlers and first to interact with the user.
First, it starts the db_controller, then launches the app.

Send anything to initiate the bot.

Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""

# Importing General modules
import asyncio
from datetime import datetime, timedelta
import argparse

# Importing Project-specific modules

from logger import log_action as log
import config
import group_handler

# Importing python-telegram-bot modules

from telegram import __version__ as TG_VER

try:
    from telegram import __version_info__
except ImportError:
    __version_info__ = (0, 0, 0, 0, 0)  # type: ignore[assignment]

if __version_info__ < (20, 0, 0, "alpha", 1):
    raise RuntimeError(
        f"This bot is not compatible with your current PTB version {TG_VER}."
    )
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackContext,
    MessageHandler,
    filters,
)

parser = argparse.ArgumentParser(description="There should be a help intro.",
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("-f", "--fill-none-values", action="store_true", help="update db with new values")

args = parser.parse_args()

class BotSession:
    def __init__(self):
        self.overlord = int(config.OVERLORD_USER_ID)

        self.user_time_stamps = {}
        self.scheduled_job = None
        self.request_time = config.REQUEST_TIME
        self.max_request = config.MAX_REQUEST
        self.start = config.START
        self.inverval = config.INTERVAL
        self.end = config.END

        self.respond = True # Do not respond to user requests
        self.use_info = False # Print extra info for each schedule requests

        self.current_group = None

    def get_chat_id(self, chat_id = None):
        # If chat_id in group_data then return it,
        # else return False
        chat_id = chat_id if chat_id else str(self.current_group)
        print(chat_id)
        group_db = group_handler.get_approved_groups()
        if chat_id not in group_db.keys():
            return False
        return self.current_group

c_session = BotSession()

async def check_group(update: Update, context: CallbackContext) -> bool:
    user_id = update.message.from_user.id
    if user_id == c_session.overlord:
        return True
    chat_id = update.message.chat_id
    if not c_session.get_chat_id(chat_id):
        print(user_id, chat_id)
        await context.bot.send_message(update.effective_chat.id,"You're not authorized to use this bot.")
        return False
    return True

async def rate_limit(update: Update, context: CallbackContext) -> bool:
    user_id = update.message.from_user.id
    if user_id == c_session.overlord:
        return True

    now = datetime.now()
    if user_id in c_session.user_time_stamps:
        time_stamps = c_session.user_time_stamps[user_id]
        time_stamps = [t for t in time_stamps if now - t < timedelta(minutes=c_session.request_time)]

        if len(time_stamps) >= c_session.max_request:
            await context.bot.send_message(update.effective_chat.id,"You've exceeded the maximum number of requests. Please wait.")
            return False

        time_stamps.append(now)
    else:
        c_session.user_time_stamps[user_id] = [now]

    return True

async def add_group(update,context):
    """Add group to group_data by its chat_id."""
    if update.message.from_user.id != c_session.overlord:
        await unknown(update, context)
        return
    chat_id = update.message.chat_id
    group_handler.add_new_group(chat_id)
    log("bot handler",f"Overlord has added group with chat_id:{chat_id}")

async def remove_group(update,context):
    """Move group info to removed_data by its chat_id."""
    if update.message.from_user.id != c_session.overlord:
        await unknown(update, context)
        return
    chat_id = update.message.chat_id
    group_handler.remove_approved_group(chat_id)
    log("bot handler",f"Overlord has removed group with chat_id:{chat_id}")

async def toggle_respond(update: Update, context: CallbackContext) -> None:
    if update.message.from_user.id != c_session.overlord:
        await unknown(update, context)
        return
    respond = c_session.respond
    respond = not respond
    c_session.respond = respond
    status = "undeafed" if respond else "deafed"
    log("bot handler", f"Overlord has {status} user respond")

async def toggle_info(update: Update, context: CallbackContext) -> None:
    if update.message.from_user.id != c_session.overlord:
        await unknown(update, context)
        return
    use_info = c_session.use_info
    use_info = not use_info
    c_session.use_info = use_info
    status = "verbose" if use_info else "no info"
    log("bot handler", f"Overlord has toggled {status} mode")

async def handle_message(update: Update, context: CallbackContext) -> bool:
    user_id = update.message.from_user.id
    if not c_session.respond and user_id != c_session.overlord:
        return False

    if not await check_group(update, context) or not await rate_limit(update, context):
        return False
    return True

# Schedule Handlers

async def schedule_now(update: Update, context: CallbackContext) -> None:
    """Reply a info about current lesson."""
    if not await handle_message(update, context):
        return
    if c_session.use_info:
        info = True
    else:
        info = False
    await context.bot.send_message(update.effective_chat.id,
                                   config.form_message(1,link=1,info=info),
                                   disable_web_page_preview=True,
                                   parse_mode='Markdown')

async def schedule_today(update: Update, context: CallbackContext) -> None:
    """Reply a info about today's lessons."""
    if not await handle_message(update, context):
        return
    if c_session.use_info:
        info = True
    else:
        info = False
    await context.bot.send_message(update.effective_chat.id,
                                   config.form_message(2,link=1,info=info),
                                   disable_web_page_preview=True,
                                   parse_mode='Markdown')

async def schedule_this_week(update: Update, context: CallbackContext) -> None:
    """Reply a info about this week's lessons."""
    if not await handle_message(update, context):
        return
    if c_session.use_info:
        info = True
    else:
        info = False
    await context.bot.send_message(update.effective_chat.id,
                                   config.form_message(3,link=info,info=info),
                                   disable_web_page_preview=True,
                                   parse_mode='Markdown')

async def schedule_all(update: Update, context: CallbackContext) -> None:
    """Reply a info about all lessons."""
    if not await handle_message(update, context):
        return
    if c_session.use_info:
        info = True
    else:
        info = False
    await context.bot.send_message(update.effective_chat.id,
                                   config.form_message(4,link=info,info=info),
                                   disable_web_page_preview=True,
                                   parse_mode='Markdown')

async def unknown(update: Update, context: CallbackContext) -> None:
    """Notify that missing command in unknown."""
    if not await handle_message(update, context):
        return
    await context.bot.send_message(update.effective_chat.id,
        text="Sorry, I didn't understand that command.",
    )

async def start_scheduler(update: Update, context: CallbackContext) -> None:
    if update.message.from_user.id != c_session.overlord:
        await unknown(update, context)
        return
    c_session.current_group = update.message.chat_id
    if c_session.scheduled_job is None:
        c_session.scheduled_job = context.job_queue.run_repeating(callback_send_message, first=c_session.start, interval=c_session.inverval, last=c_session.end)
        log("bot handler","Overlord has started a scheduler")
    else:
        log("bot handler","Scheduler is already running.")

async def callback_send_message(context: CallbackContext) -> None:
    """Reply a info about current lesson."""
    chat_id = c_session.get_chat_id()
    if not chat_id:
        return
    if c_session.use_info:
        info = True
    else:
        info = False
    message = config.form_message(0,link=1,info=info)
    await context.bot.send_message(c_session.get_chat_id(),message,
                                   disable_web_page_preview=True,
                                   parse_mode='Markdown')

async def stop_scheduler(update: Update, context: CallbackContext) -> None:
    if update.message.from_user.id != c_session.overlord:
        await unknown(update, context)
        return
    if c_session.scheduled_job is not None:
        c_session.scheduled_job.schedule_removal()
        c_session.scheduled_job = None
        log("bot handler","Overlord has stopped a scheduler")
    else:
        log("bot handler","Scheduler is not running.")

def main() -> None:

    if args.fill_none_values:
        config.fill_none_values()

    app = Application.builder().token(config.AUTH_TOKEN).build()

    # Instance handlers
    unknown_handler = MessageHandler(filters.COMMAND, unknown)
    sch_now_handler = CommandHandler("now", schedule_now)
    sch_today_handler = CommandHandler("today", schedule_today)
    sch_this_week_handler = CommandHandler("week", schedule_this_week)
    toggle_respond_handler = CommandHandler("deaf", toggle_respond)
    toggle_info_handler = CommandHandler("verbose", toggle_info)
    add_group_handler = CommandHandler("addThisGroup", add_group)
    remove_group_handler = CommandHandler("removeThisGroup", remove_group)
    start_scheduler_handler = CommandHandler("start",start_scheduler)
    stop_scheduler_handler = CommandHandler("stop",stop_scheduler)

    sch_all_handler = CommandHandler("all", schedule_all)

    # Add handlers
    app.add_handler(sch_now_handler)
    app.add_handler(sch_today_handler)
    app.add_handler(sch_this_week_handler)
    app.add_handler(toggle_respond_handler)
    app.add_handler(toggle_info_handler)
    app.add_handler(add_group_handler)
    app.add_handler(remove_group_handler)
    app.add_handler(start_scheduler_handler)
    app.add_handler(stop_scheduler_handler)
    app.add_handler(sch_all_handler)

    # This must be the last handler!!!!!
    app.add_handler(unknown_handler)

    app.run_polling()

if __name__ == "__main__":
    main()

