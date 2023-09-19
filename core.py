"""This is the core of the bot. It launches the app,
maintain handlers and first to interact with the user.

Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""

# Importing General modules
from datetime import datetime, timedelta, time
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
from telegram import (
    Update,
    BotCommand,
    BotCommandScopeChat,
    BotCommandScopeChatAdministrators,
    BotCommandScopeChatMember
)
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
parser.add_argument("-f", "--fill-none-values", action="store_true",
                    help="update db with new values")
args = parser.parse_args()


# Constants
MESSAGE_NOW = 0
MESSAGE_TODAY = 1
MESSAGE_WEEK = 2
MESSAGE_ALL = 3

# Define common, admin, and overlord commands
COMMON_COMMANDS = [
    BotCommand("now", "Показати яка зараз пара та наступну"),
    BotCommand("today", "Показати розклад на цей день"),
    BotCommand("week", "Показати розклад на цей тиждень"),
    BotCommand("all", "Показати повний розклад")
]

ADMIN_COMMANDS = COMMON_COMMANDS + [
    BotCommand("verbose", "Показувати більше/менше інформації у розкладах"),
    BotCommand("deaf", "Дозволити/заборонити учасникам працювати з ботом")
]

OVERLORD_COMMANDS = ADMIN_COMMANDS + [
    BotCommand("enable", "Let this group use the bot"),
    BotCommand("disable", "Forbid use of the bot for this group"),
    BotCommand("start_scheduler", "Start schedule"),
    BotCommand("stop_scheduler", "Stop schedule"),
    BotCommand("start", "Welcome message"),
    BotCommand("autodelete", "Create a job to delete bot messages and user commands")
]

class BotSession:
    def __init__(self):
        self.overlord = config.OVERLORD_USER_ID  # Admin user ID
        self.text = config.TEXT  # Text templates for bot messages

        # Deque to hold timestamps for rate-limiting
        self.global_time_stamps = deque()

        self.scheduled_jobs = None  # Holds the scheduled job objects
        self.request_time = config.REQUEST_TIME  # Time window for rate-limiting
        self.max_request = config.MAX_REQUEST  # Max requests in time window

        # Scheduler settings
        self.start = config.START  # Scheduler start time
        self.interval = config.INTERVAL  # Scheduler interval
        self.end = config.END  # Scheduler end time

        self.respond = True  # Toggle for bot to respond to user requests
        self.use_info = False  # Toggle for extra info in scheduled requests
        self.autodelete = False # Toggle to automatically delete message
        self.autodelete_job = None
        self.autodelete_interval = config.AUTODELETE

        self.chat_info = {} # Store all chat info for future use
        self.bot_message_ids = []  # Store bot's message IDs for deletion
        self.user_message_ids = []  # Store user's message IDs for deletion

    def get_chat_id(self, chat_id=None):
        # Get the chat ID, default to current group if not specified
        chat_id = chat_id if chat_id else str(self.chat_info["chat_id"])

        # Fetch group data from database
        group_dict = group_handler.get_groups_as_dict()

        # Check if chat ID exists in group data
        if str(chat_id) not in group_dict.keys():
            return False

        # Set current group chat ID
        self.chat_info["chat_id"] = chat_id
        return chat_id

session = BotSession()



######################################################################
###################### Helper functions ##############################
######################################################################

# Convert time string to datetime.time object with UTC offset
def get_time_with_utc_offset(time_str: str, utc_offset: int) -> time:
    """Convert time string to datetime.time with UTC offset."""
    parsed_time = datetime.strptime(time_str, "%H:%M").time()
    today = datetime.utcnow().date()
    combined_time = datetime.combine(today, parsed_time)
    offset_time = (combined_time + timedelta(hours=utc_offset)).time()
    return offset_time

# Get chat info like chat_id, user_id, message_id, and chat_admins
async def get_chat_info(update: Update, context: CallbackContext) -> None:
    """Retrieve essential chat information."""
    chat_id = update.effective_chat.id
    chat_admins = await context.bot.get_chat_administrators(chat_id)

    session.chat_info = {
        'chat_id': chat_id,
        'chat_admins': chat_admins
    }

# Check if a user is an admin in the group
def is_admin(user_id, chat_admins) -> bool:
    """Check if user is an admin."""
    try:
        return user_id in [admin.user.id for admin in chat_admins]
    except Exception as e:
        print(f"Error: {e}")
        return False

# Check if the chat_id belongs to an authorized group
def check_group(chat_id: int) -> bool:
    """Verify if chat is authorized."""
    return bool(session.get_chat_id(chat_id))

# Implement rate limiting for bot requests
def rate_limit() -> bool:
    """Global rate limiting."""
    now = datetime.now()
    time_limit = timedelta(minutes=session.request_time)
    while session.global_time_stamps and now - session.global_time_stamps[0] > time_limit:
        session.global_time_stamps.popleft()
    if len(session.global_time_stamps) >= session.max_request:
        return False
    session.global_time_stamps.append(now)
    return True

# Handle incoming messages and perform checks
def handle_message(user_id: int, chat_id: int, chat_admins: tuple) -> bool:
    """Handle incoming messages and perform necessary checks."""

    # If the user is an admin, no further checks are needed
    if is_admin(user_id, chat_admins):

        # If the bot is set to not respond, exit early
        if not session.respond:
            return False

        # Check if the chat is authorized
        if not check_group(chat_id):  # Removed 'await' as check_group is not async
            return "auth"

        # Check for rate limiting
        if not rate_limit():  # Removed 'await' as rate_limit is not async
            return "limit"

    return True

async def error_respond_message(context: CallbackContext, type_: str) -> None:
    """Send message to notify about certain error or restriction"""
    if type_ == "auth":
        return await context.bot.send_message(session.chat_info['chat_id'], session.text.no_auth)
    elif type_ == "limit":
        return await context.bot.send_message(session.chat_info['chat_id'], session.text.request_limit)

# Notify for unknown commands
async def unknown(update: Update, context: CallbackContext):
    """Handle unknown commands."""
    return await context.bot.send_message(update.effective_chat.id,
                                   text=session.text.unknown_command)

# Delete bot and user messages
async def delete_message(context: CallbackContext):
    """Delete bot and user messages."""
    for msg_list in [session.bot_message_ids, session.user_message_ids]:
        while msg_list:
            msg_id = msg_list.pop(0)
            try:
                await context.bot.delete_message(session.chat_info['chat_id'], msg_id)
            except Exception as e:
                log("bot handler", f"Failed to delete message: {e}")
                break
    log("bot handler", "Finished deleting messages")

# Toggle boolean state
def toggle_state(state: bool) -> bool:
    """Toggle boolean state."""
    return not state




######################################################################
###################### Admin only functions ##########################
######################################################################

######################### OVERLORD ONLY ##############################

# Start command for the bot
async def start(update: Update, context: CallbackContext) -> None:
    """Send a welcome message if the user is the overlord."""
    # Store the user's message ID for future deletion
    session.user_message_ids.append(update.message.message_id)

    if str(update.effective_user.id) != session.overlord:
        session.bot_message_ids.append((await unknown(update, context)).message_id)
        return
    await context.bot.send_message(
        update.effective_chat.id, config.get_welcome_message(),
        disable_web_page_preview=True, parse_mode='MarkdownV2'
    )

# Add commands for different user roles
async def addcommands(update: Update, context: CallbackContext) -> None:
    """Add bot commands for users, admins, and the overlord."""
    # Store the user's message ID for future deletion
    session.user_message_ids.append(update.message.message_id)

    if str(update.effective_user.id) != session.overlord:
        session.bot_message_ids.append((await unknown(update, context)).message_id)
        return
    chat_id = update.effective_chat.id

    # Set commands for different scopes
    await context.bot.set_my_commands(COMMON_COMMANDS, scope=BotCommandScopeChat(chat_id))
    await context.bot.set_my_commands(ADMIN_COMMANDS, scope=BotCommandScopeChatAdministrators(chat_id))
    await context.bot.set_my_commands(OVERLORD_COMMANDS, scope=BotCommandScopeChatMember(chat_id, session.overlord))
    log("bot handler", 'Commands added for administrators.')

# General function to manage groups
async def manage_group(update: Update, context: CallbackContext, action: str) -> None:
    """Add or remove a group based on the action."""
    if str(update.message.from_user.id) != session.overlord:
        session.bot_message_ids.append((await unknown(update, context)).message_id)
        return
    chat_id = update.message.chat_id

    if action == "add":
        group_handler.add_group(chat_id)
    elif action == "remove":
        group_handler.remove_group(chat_id)

# Add a group
async def add_group(update, context):
    """Wrapper for adding a group."""
    # Store the user's message ID for future deletion
    session.user_message_ids.append(update.message.message_id)

    await manage_group(update, context, "add")

# Remove a group
async def remove_group(update, context):
    """Wrapper for removing a group."""
    # Store the user's message ID for future deletion
    session.user_message_ids.append(update.message.message_id)

    await manage_group(update, context, "remove")

async def toggle_autodeletion(update: Update, context: CallbackContext) -> None:
    # Store the user's message ID for future deletion
    session.user_message_ids.append(update.message.message_id)

    """Toggle the verbosity of the bot."""
    if str(update.message.from_user.id) != session.overlord:
        session.bot_message_ids.append((await unknown(update, context)).message_id)
        return

    if session.autodelete is None:
        session.autodelete = []

    # Toggle autodelete
    session.autodelete = toggle_state(session.autodelete)
    status = "enabled" if session.autodelete else "disabled"
    if session.autodelete:
        if not session.autodelete_job:
            session.autodelete_job = context.job_queue.run_repeating(
                        delete_message,
                        first=0,
                        interval=session.autodelete_interval,
            )
    else:
        try:
            session.autodelete_job.schedule_removal()
        except Exception as e:
            log("bot handler", f"Failed to remove autodelete job: {e}")
    log("bot handler", f"Admin has {status} autodelete mode")

async def manage_scheduler(update: Update, context: CallbackContext, action: str) -> None:
    """General function to start or stop the scheduler based on the action parameter."""
    if str(update.message.from_user.id) != session.overlord:
        session.bot_message_ids.append((await unknown(update, context)).message_id)
        return

    # Required for callback_send_message
    if not session.chat_info:
        await get_chat_info(update, context)

    # Initialize scheduled_job list if it doesn't exist
    if session.scheduled_jobs is None:
        session.scheduled_jobs = []

    # If scheduler was launched after start time, start scheduler one minute later
    if action == "start":
        if not session.scheduled_jobs:
            initial_first = get_time_with_utc_offset(session.start, -3)
            interval = session.interval
            last = get_time_with_utc_offset(session.end, -3).replace(tzinfo=None)

            # Create datetime objects for better comparison
            today = datetime.now().date()
            now = datetime.now().time()
            now_with_offset = get_time_with_utc_offset(now.strftime("%H:%M"), -3)
            now_datetime = datetime.combine(today, now_with_offset).replace(tzinfo=None)
            first_datetime = datetime.combine(today, initial_first).replace(tzinfo=None)
            last_datetime = datetime.combine(today, last).replace(tzinfo=None)

            if first_datetime < now_datetime < last_datetime:
                log("bot handler","Admin launched scheduler later then excpected!")
                first_datetime = now_datetime + timedelta(minutes=1)
                first = first_datetime.time()
                log("bot_handler",f"New first time for today: {first}")

                job_today = context.job_queue.run_repeating(
                    callback_send_message,
                    first=first,
                    last=last,
                    interval=interval,
                )
                session.scheduled_jobs.append(job_today)
                log("bot handler", "Admin has started a scheduler for today")

                # Set it to start the next day with the initial value
                first_datetime = datetime.combine(today + timedelta(days=1), initial_first)
                first = first_datetime.time()
                log("bot_handler",f"First time for next day: {first}")

                # Schedule job for the next day
                job_next_day = context.job_queue.run_repeating(
                    callback_send_message,
                    first=first,
                    interval=interval,
                )
                session.scheduled_jobs.append(job_next_day)
                log("bot handler", "Admin has scheduled a job for the next day")
            elif now_datetime < last_datetime:
                log("bot handler","Admin launched scheduler after the end of today's schedule!")
                # Set it to start the next day with the initial value
                first_datetime = datetime.combine(today + timedelta(days=1), initial_first)
                first = first_datetime.time()
                log("bot_handler",f"First time for next day: {first}")

                # Schedule job for the next day
                job_next_day = context.job_queue.run_repeating(
                    callback_send_message,
                    first=first,
                    interval=interval,
                )
                session.scheduled_jobs.append(job_next_day)
                log("bot handler", "Admin has scheduled a job for the next day")
            else:
                # Regular scheduling logic
                job_regular = context.job_queue.run_repeating(
                    callback_send_message,
                    first=initial_first,
                    interval=interval,
                )
                session.scheduled_jobs.append(job_regular)
                log("bot handler", "Admin has started a scheduler")
        else:
            log("bot handler", "Scheduler is already running.")
    elif action == "stop":
        if not session.scheduled_jobs:
            log("bot_handler", "Scheduler is not running.")
            return
        while session.scheduled_jobs:
            scheduled_job = session.scheduled_jobs.pop(0)
            try:
                scheduled_job.schedule_removal()
            except Exception as e:
                log("bot handler", f"Failed to remove a job: {e}")
        log("bot handler", "Admin has stopped a scheduler")

async def start_scheduler(update: Update, context: CallbackContext) -> None:
    """Start the scheduler."""
    # Store the user's message ID for future deletion
    session.user_message_ids.append(update.message.message_id)

    await manage_scheduler(update, context, "start")

async def stop_scheduler(update: Update, context: CallbackContext) -> None:
    """Stop the scheduler."""
    # Store the user's message ID for future deletion
    session.user_message_ids.append(update.message.message_id)

    await manage_scheduler(update, context, "stop")

async def callback_send_message(context: CallbackContext) -> None:
    """Reply with info about the current lesson."""
    chat_id = session.get_chat_id()
    if not chat_id:
        return

    info = session.use_info  # This seems to be a boolean, so should be directly usable.
    message = config.form_message(MESSAGE_NOW, link=True, info=info,
                                  return_false=True, callback_message=True)
    if not message:
        return

    sent_message = await context.bot.send_message(
        chat_id,
        message,
        disable_web_page_preview=True,
        parse_mode='Markdown'
    )

    # Store the bot's message ID for future deletion
    session.bot_message_ids.append(sent_message.message_id)

########################## ALL ADMINS ################################

async def toggle_respond(update: Update, context: CallbackContext) -> None:
    """Toggle the bot's ability to respond."""
    # Store the user's message ID for future deletion
    session.user_message_ids.append(update.message.message_id)

    # Retrieve chat and user information
    if not session.chat_info:
        await get_chat_info(update, context)


    chat_id = session.chat_info['chat_id']
    chat_admins = session.chat_info['chat_admins']
    user_id = update.effective_user.id

    if str(update.message.from_user.id) != session.overlord:
        if not check_group(chat_id):
            session.bot_message_ids.append((await error_respond_message(context,"auth")).message_id)
            return False

        # Check if the user is an admin
        if not is_admin(user_id, chat_admins):
            session.bot_message_ids.append((await unknown(update, context)).message_id)
            return

        # Retrieve the text and status for the deaf mode
    text, off, on = session.text.deaf_mode
    session.respond = toggle_state(session.respond)
    status = (on, "enabled") if not session.respond else (off, "disabled")
    sent_message = await context.bot.send_message(chat_id,
                                                      f"{text} {status[0]}")
    log("bot handler", f"Admin has {status[1]} deaf mode")

        # Store the bot's message ID for future deletion
    session.bot_message_ids.append(sent_message.message_id)

async def toggle_info(update: Update, context: CallbackContext) -> None:
    """Toggle the verbosity of the bot."""
    # Store the user's message ID for future deletion
    session.user_message_ids.append(update.message.message_id)

    # Retrieve chat and user information
    if not session.chat_info:
        await get_chat_info(update, context)

    chat_id = session.chat_info['chat_id']
    chat_admins = session.chat_info['chat_admins']
    user_id = update.effective_user.id

    if str(update.message.from_user.id) != session.overlord:
        if not check_group(chat_id):
            session.bot_message_ids.append((await error_respond_message(context,"auth")).message_id)
            return False

        # Check if the user is an admin
        if not is_admin(user_id, chat_admins):
            session.bot_message_ids.append((await unknown(update, context)).message_id)
            return

    # Retrieve the text and status for verbose mode
    text, off, on = session.text.verbose_mode
    session.use_info = toggle_state(session.use_info)
    status = (on, "enabled") if session.use_info else (off, "disabled")
    sent_message = await context.bot.send_message(chat_id,
                                                      f"{text} {status[0]}")
    log("bot handler", f"Admin has {status[1]} verbose mode")

    # Store the bot's message ID for future deletion
    session.bot_message_ids.append(sent_message.message_id)

### Managing scheduler

######################################################################
########################### USER functions ###########################
######################################################################

async def send_schedule_message(update: Update, context: CallbackContext, message_type: int) -> None:
    """General function to handle sending schedule messages."""
    # Retrieve chat and user information
    if not session.chat_info:
        await get_chat_info(update, context)

    chat_id = session.chat_info['chat_id']
    chat_admins = session.chat_info['chat_admins']
    user_id = update.effective_user.id

    if str(update.message.from_user.id) != session.overlord:

        handled_message = handle_message(user_id=user_id,chat_id=chat_id, chat_admins=chat_admins)

        if not check_group(chat_id):
            session.bot_message_ids.append((await error_respond_message(context,"auth")).message_id)
            return False

        if not handled_message:
            return

        elif handled_message in ("auth", "limit"):
            session.bot_message_ids.append((await error_respond_message(context, handled_message)).message_id)
            return

    info = session.use_info  # This appears to be a boolean, so it should be directly usable
    message = config.form_message(message_type, link=info, info=info)
    message_ids = []

    if message_type == MESSAGE_ALL:
        week_messages = message.split("%%")
        for msg in week_messages:
            sent_message = await context.bot.send_message(chat_id, msg,
                                           disable_web_page_preview=True,
                                           parse_mode='Markdown')
            message_ids.append(sent_message.message_id)
    else:
        sent_message = await context.bot.send_message(chat_id, message,
                                       disable_web_page_preview=True,
                                       parse_mode='Markdown')
        message_ids.append(sent_message.message_id)

    # Store the current message_ids for future deletion
    session.bot_message_ids = session.bot_message_ids + message_ids

async def schedule_now(update: Update, context: CallbackContext) -> None:
    """Reply info about the current lesson."""
    # Store the user's message ID for future deletion
    session.user_message_ids.append(update.message.message_id)

    await send_schedule_message(update, context, MESSAGE_NOW)

async def schedule_today(update: Update, context: CallbackContext) -> None:
    """Reply info about today's lessons."""
    # Store the user's message ID for future deletion
    session.user_message_ids.append(update.message.message_id)

    await send_schedule_message(update, context, MESSAGE_TODAY)

async def schedule_this_week(update: Update, context: CallbackContext) -> None:
    """Reply info about this week's lessons."""
    # Store the user's message ID for future deletion
    session.user_message_ids.append(update.message.message_id)

    await send_schedule_message(update, context, MESSAGE_WEEK)

async def schedule_all(update: Update, context: CallbackContext) -> None:
    """Reply info about all lessons."""
    # Store the user's message ID for future deletion
    session.user_message_ids.append(update.message.message_id)

    await send_schedule_message(update, context, MESSAGE_ALL)


###############
#MAIN#FUNCTION#
###############

def main():
    """Main function"""
    if args.fill_none_values:
        config.fill_none_values()
        sys.exit()

    app = Application.builder().token(config.AUTH_TOKEN).build()

    # Handlers
    handlers = [
        CommandHandler("now", schedule_now),
        CommandHandler("today", schedule_today),
        CommandHandler("week", schedule_this_week),
        CommandHandler("deaf", toggle_respond),
        CommandHandler("verbose", toggle_info),
        CommandHandler("enable", add_group),
        CommandHandler("disable", remove_group),
        CommandHandler("start_scheduler", start_scheduler),
        CommandHandler("stop_scheduler", stop_scheduler),
        CommandHandler("all", schedule_all),
        CommandHandler('commands', addcommands),
        CommandHandler("start", start),
        CommandHandler("autodelete",toggle_autodeletion),
        MessageHandler(filters.COMMAND, unknown)  # This must be the last handler
    ]

    for handler in handlers:
        app.add_handler(handler)

    app.run_polling()

if __name__ == "__main__":
    main()
