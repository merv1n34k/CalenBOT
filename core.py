"""This is the core of the bot. It launches the app,
maintain handlers and first to interact with the user.
First, it starts the db_controller, then launches the app.

Send anything to initiate the bot.

Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""

# Importing General modules
from datetime import datetime, timedelta
from collections import deque
import argparse
import sys

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
from telegram import Update, BotCommand, BotCommandScopeChatAdministrators, BotCommandScopeChatMember
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
        self.overlord = config.OVERLORD_USER_ID

        self.global_time_stamps = deque()
        self.scheduled_job = None
        self.request_time = config.REQUEST_TIME
        self.max_request = config.MAX_REQUEST
        self.start = config.START
        self.interval = config.INTERVAL
        self.end = config.END

        self.respond = True # Do not respond to user requests
        self.use_info = False # Print extra info for each schedule requests

        self.current_group = None
        self.last_bot_message_id = None
        self.last_user_message_id = None


    def get_chat_id(self, chat_id = None):
        # If chat_id in group_data then return it,
        # else return False
        chat_id = chat_id if chat_id else str(self.current_group)
        #print(chat_id)
        group_db = group_handler.get_groups_as_dict()
        if str(chat_id) not in group_db.keys():
            return False
        self.current_group = chat_id
        return self.current_group

c_session = BotSession()

# Helper functions

async def start(update: Update, context: CallbackContext) -> None:
    if str(update.effective_user.id) != c_session.overlord:
        await unknown(update, context)
        return
    await context.bot.send_message(update.effective_chat.id, config.get_welcome_message(),
        disable_web_page_preview=True,
        parse_mode='MarkdownV2')

async def addcommands(update: Update, context: CallbackContext) -> None:
    if str(update.effective_user.id) != c_session.overlord:
        await unknown(update, context)
        return
    chat_id = update.effective_chat.id

    # Common commands for administrators
    admin_commands = [
        BotCommand("now", "Print current lesson info"),
        BotCommand("today", "Print a schedule today"),
        BotCommand("week", "Print a schedule for this week"),
        BotCommand("all","Print a complete schedule"),
        BotCommand("verbose", "Toggle printing more info"),
        BotCommand("deaf", "Toggle bot response to user requests"),
    ]

    overlord_commands = [
        BotCommand("now", "Print current lesson info"),
        BotCommand("today", "Print a schedule today"),
        BotCommand("week", "Print a schedule for this week"),
        BotCommand("all","Print a complete schedule"),
        BotCommand("verbose", "Verbose mode"),
        BotCommand("deaf", "Deaf mode"),
        BotCommand("enable", "Let this group use the bot"),
        BotCommand("disable", "Forbit use of the bot for this group"),
        BotCommand("start_scheduler", "Start schedule"),
        BotCommand("stop_scheduler", "Stop schedule")
    ]

    # Set commands for chat administrators
    scope_admins = BotCommandScopeChatAdministrators(chat_id)
    scope_overlord  = BotCommandScopeChatMember(chat_id, c_session.overlord)
    await context.bot.set_my_commands(admin_commands, scope=scope_admins)
    await context.bot.set_my_commands(overlord_commands, scope=scope_overlord)

    log("bot handler",'Commands added for administrators.')

async def is_admin(update: Update, context: CallbackContext) -> bool:
    """Check if the user is an admin in the group."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    try:
        chat_admins = await context.bot.get_chat_administrators(chat_id)
        admin_ids = [admin.user.id for admin in chat_admins]
        return user_id in admin_ids
    except Exception as e:
        print(f"An error occurred: {e}")
        return False

async def check_group(chat_id: int) -> bool:
    """Check if the user belongs to an authorized group."""
    if not c_session.get_chat_id(chat_id):
        return False
    return True

async def rate_limit() -> bool:
    """Rate limit requests globally."""
    now = datetime.now()

    # Remove timestamps older than the rate-limiting window
    while c_session.global_time_stamps and now - global_time_stamps[0] > timedelta(minutes=c_session.request_time):
        global_time_stamps.popleft()

    # Check if rate limit has been exceeded
    if len(global_time_stamps) >= c_session.max_request:
        return False

    # Add the current timestamp
    global_time_stamps.append(now)

    return True

async def handle_message(update: Update, context: CallbackContext) -> bool:
    """Handle incoming messages and perform necessary checks."""
    chat_id = update.message.chat_id

    if await is_admin(update, context):
        return True
    if not c_session.respond:
        return False

    if not await check_group(chat_id):
        await context.bot.send_message(update.effective_chat.id, "You're not authorized to use this bot.")
        return False

    if not await rate_limit():
        await context.bot.send_message(update.effective_chat.id, "Rate limit exceeded. Please wait.")
        return False
    return True

async def unknown(update: Update, context: CallbackContext) -> None:
    """Notify that entered command in unknown."""
    if not await handle_message(update, context):
        return
    await context.bot.send_message(update.effective_chat.id,
        text="Sorry, I didn't understand that command.")

async def delete_message(context: CallbackContext, chat_id: int):
    # Delete bot's last message if it exists
    if c_session.last_bot_message_id:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=c_session.last_bot_message_id)
        except Exception as e:
            log("bot handler", f"Failed to delete user's last command message: {e}")

    # Delete user's last command message if it exists
    if c_session.last_user_message_id:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=c_session.last_user_message_id)
        except Exception as e:
            log("bot handler", f"Failed to delete user's last command message: {e}")

# Admin functions

async def toggle_state(state: bool) -> bool:
    """Toggle the state of a boolean variable."""
    return not state

async def manage_group(update: Update, context: CallbackContext, action: str) -> None:
    """General function to add or remove a group."""
    if str(update.message.from_user.id) != c_session.overlord:
        await unknown(update, context)
        return

    chat_id = update.message.chat_id

    if action == "add":
        group_handler.add_group(chat_id)
    elif action == "remove":
        group_handler.remove_group(chat_id)

async def add_group(update, context):
    """Add a group."""
    await manage_group(update, context, "add")

async def remove_group(update, context):
    """Remove a group."""
    await manage_group(update, context, "remove")

async def toggle_respond(update: Update, context: CallbackContext) -> None:
    if not await is_admin(update, context):
        await unknown(update, context)
        return

    c_session.respond = toggle_state(c_session.respond)
    status = "undeafed" if c_session.respond else "deafed"
    log("bot handler", f"Admin has {status} user respond")

async def toggle_info(update: Update, context: CallbackContext) -> None:
    if not await is_admin(update, context):
        await unknown(update, context)
        return

    c_session.use_info = toggle_state(c_session.use_info)
    status = "verbose" if c_session.use_info else "no info"
    log("bot handler", f"Admin has toggled {status} mode")

# Managing scheduler

async def manage_scheduler(update: Update, context: CallbackContext, action: str) -> None:
    """General function to start or stop the scheduler based on the action parameter."""
    if not await is_admin(update, context):
        await unknown(update, context)
        return
    c_session.current_group = update.message.chat_id

    if action == "start":
        if c_session.scheduled_job is None:
            c_session.scheduled_job = context.job_queue.run_repeating(
                callback_send_message,
                first=0,#datetime.strptime(c_session.start, '%H:%M').time(),
                interval=10,#c_session.interval,
                #last=datetime.strptime(c_session.end, '%H:%M').time()
            )
            log("bot handler", "Admin has started a scheduler")
        else:
            log("bot handler", "Scheduler is already running.")
    elif action == "stop":
        if c_session.scheduled_job is not None:
            c_session.scheduled_job.schedule_removal()
            c_session.scheduled_job = None
            log("bot handler", "Admin has stopped a scheduler")
        else:
            log("bot_handler", "Scheduler is not running.")

async def start_scheduler(update: Update, context: CallbackContext) -> None:
    """Start the scheduler."""
    await manage_scheduler(update, context, "start")

async def stop_scheduler(update: Update, context: CallbackContext) -> None:
    """Stop the scheduler."""
    await manage_scheduler(update, context, "stop")

async def callback_send_message(context: CallbackContext) -> None:
    """Reply with info about the current lesson."""
    chat_id = c_session.get_chat_id()
    if not chat_id:
        return

    info = c_session.use_info  # This seems to be a boolean, so should be directly usable.
    message = config.form_message(MESSAGE_NOW, link=True, info=info, return_false=True)
    if not message:
        return

    await context.bot.send_message(
        chat_id,
        message,
        disable_web_page_preview=True,
        parse_mode='Markdown'
    )

# All Schedule commands
MESSAGE_NOW = 0
MESSAGE_TODAY = 1
MESSAGE_WEEK = 2
MESSAGE_ALL = 3

async def send_schedule_message(update: Update, context: CallbackContext, message_type: int) -> None:
    """General function to handle sending schedule messages."""
    if not await handle_message(update, context):
        return
    info = c_session.use_info  # This appears to be a boolean, so it should be directly usable
    message = config.form_message(message_type, link=info, info=info)
    chat_id = update.effective_chat.id

    if message_type == MESSAGE_ALL:
        week_messages = message.split("%%")
        for msg in week_messages:
            sent_message = await context.bot.send_message(chat_id, msg,
                                           disable_web_page_preview=True,
                                           parse_mode='Markdown')
    else:
        sent_message = await context.bot.send_message(chat_id, message,
                                       disable_web_page_preview=True,
                                       parse_mode='Markdown')
    await delete_message(context,chat_id)
    # Store the current message_ids for future deletion
    c_session.last_bot_message_id = sent_message.message_id

async def schedule_now(update: Update, context: CallbackContext) -> None:
    """Reply info about the current lesson."""
    await send_schedule_message(update, context, MESSAGE_NOW)
    c_session.last_user_message_id = update.message.message_id

async def schedule_today(update: Update, context: CallbackContext) -> None:
    """Reply info about today's lessons."""
    await send_schedule_message(update, context, MESSAGE_TODAY)
    c_session.last_user_message_id = update.message.message_id

async def schedule_this_week(update: Update, context: CallbackContext) -> None:
    """Reply info about this week's lessons."""
    await send_schedule_message(update, context, MESSAGE_WEEK)
    c_session.last_user_message_id = update.message.message_id

async def schedule_all(update: Update, context: CallbackContext) -> None:
    """Reply info about all lessons."""
    await send_schedule_message(update, context, MESSAGE_ALL)
    c_session.last_user_message_id = update.message.message_id

# Main function

def main() -> None:

    if args.fill_none_values:
        config.fill_none_values()
        sys.exit()

    app = Application.builder().token(config.AUTH_TOKEN).build()

    # Instance handlers
    unknown_handler = MessageHandler(filters.COMMAND, unknown)
    sch_now_handler = CommandHandler("now", schedule_now)
    sch_today_handler = CommandHandler("today", schedule_today)
    sch_this_week_handler = CommandHandler("week", schedule_this_week)
    toggle_respond_handler = CommandHandler("deaf", toggle_respond)
    toggle_info_handler = CommandHandler("verbose", toggle_info)
    add_group_handler = CommandHandler("enable", add_group)
    remove_group_handler = CommandHandler("disable", remove_group)
    start_scheduler_handler = CommandHandler("start_scheduler",start_scheduler)
    stop_scheduler_handler = CommandHandler("stop_scheduler",stop_scheduler)
    add_commands_handler = CommandHandler('commands', addcommands)
    sch_all_handler = CommandHandler("all", schedule_all)
    start_handler = CommandHandler("start",start)

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
    app.add_handler(add_commands_handler)
    app.add_handler(start_handler)

    # This must be the last handler!!!!!
    app.add_handler(unknown_handler)

    app.run_polling()

if __name__ == "__main__":
    main()

