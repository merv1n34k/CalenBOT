# CalenBOT

A telegram bot for groups to send repetitive scheduled messages, such as your university's lessons schedule. Current version is *3.141*.

## Requirements

1. First thing you need is to create and activate a telegram bot in Telegram's main bot - [@BotFather](https://telegram.me/BotFather)
    * If you're not familiar how to work with `@BotFather` take a look at [this](https://core.telegram.org/bots/tutorial) Telegram's official guide.

2. This bot has the following requirements:

    * [Python](https://www.python.org/) >=3.8
    * [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) >= 20.0.0 (You can use only 20+ versions!) - asynchronous interface for the Telegram Bot API, written in Python
        * [JobQueue](https://docs.python-telegram-bot.org/en/v20.5/telegram.ext.jobqueue.html) - python-telegram-bot dependency for running scheduled commands
    * [requests](https://requests.readthedocs.io/en/latest/) - an elegant and simple HTTP library for Python, built for human beings.
    * [beautifulsoup4](https://pypi.org/project/beautifulsoup4/) - a library that makes it easy to scrape information from web pages.

## How to use

First thing to do is to `git clone` this repository, so one would run:

```bash
git clone https://github.com/merv1n34k/CalenBOT.git
cd CalenBOT
```

from this directory you should run the main Python script, conveniently named `core.py`.

To make this bot work in groups you will need to add your bot as administrator of the group, and it should have permission to *send* and *delete* messages.

To activate bot you should have a `config.py` file with all required parameters (see [config](#config)) and run the following command (example for *NIX systems):

```bash
python core.py [-f or --fill-none-values]
```

where option `-f` is a short version of `--fill-none-values`, which will prompt to fill missing values for some schedule info, such as links or teacher's info.

After that, if you want to add particular group to _approved groups_ i.e. groups that can use this bot you need to:

1. Be at least a member of this group
2. In this group send `/enable` command which will activate bot.
3. It is also recommended to send `/commands` command that will update BotMenuButtom, where you can see all bot's commands by pressing `/`.
4. Your bot is set. Users can send bot their commands, admins can control bot's behavior and _You_, as an owner of the bot, have all the commands + commands to enable/disable this bot in group + start/stop scheduler

## Config

***ATTENTION!!!*** This bot was made specifically for certain website HTML structure, if you want to use this bot for your own purpose you may need to adapt `extract_and_save_schedule` to your website. I might add a more user-friendly way to handle this issue

All configuration should be done in a `config.py` file, see `example_config.py` where you can simply put your desired values, or use default ones. So, to create configuration file on *NIX systems you can run:

```bash
cp example_config.py config.py
```

And set all your configs in this file. In particular, for this bot to work you *must* provide the following values:
* AUTH_TOKEN: your bot token
* OVERLORD_USER_ID: the user_id of a person who may control the bot
* URL: the URL for the website with your schedule in <table> tags

Other parameters are set by default, but you can change them if you need to. (see `example_config.py` for all available parameters)

## License

Distributed under the MIT License. See `LICENSE` for more information.

## Contribution

Feel free to open an issue. PRs are also appreciated.

## ROADMAP

* *Version 3.14*
    * [X] make a proper format messages
    * [X] fix scheduler and user commands
    * [X] fix `check_none` function
    * [X] add welcome message
    * [X] add option to specify multiple admins
    * [X] update `fetch_schedule`, so it is less prone to errors
    * [X] make custom menu commands for admins
    * [X] make group-broad request limits
    * [X] Bot should remove previous bot messages
    * [X] CLEANUP, REFACTORING and DOCUMENTATION
    * [X] Create a unified checker for users, admin, and overlord
    * [X] Show correct lesson on breaks

* *Version 3.141* (HERE)
    * [ ] Create a separate script for handling bot sessions
    * [ ] Implement decorators to simplify the setup of permissions for commands
    * [ ] Make it possible to control the bot from private chats (for admins!)
    * [ ] Fix scheduler launch by datetime object

* *Version 3.1415*
    * [ ] Add notification whether bot offline or online
    * [ ] add option to disable/enable lessons
    * [ ] update `<table>` tag parser so correctly extract info from most structures
    * [ ] make a correction for UTC offset in config (for now it only works for UTC+03:00)
    * [ ] admins can control bot from private chats



