# CalenBOT

***ATTENTION!!*** **This project in only in it's alpha version, many things are broken and won't work as expected! The stable version could be released in a few weeks**

A telegram bot for use in groups to send a scheduled messages such as your university's lessons schedule

## Requirements

1. First thing you need is to activate a telegram bot in Telegram's main bot - [@BotFather](https://telegram.me/BotFather)

2. To run this telegram bot, so you will need:

    * [Python](https://www.python.org/) >=3.8
    * [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) >= 20.0.0 (You can use only 20+ versions!) - asynchronous interface for the Telegram Bot API, written in Python
        * [JobQueue](https://docs.python-telegram-bot.org/en/v20.5/telegram.ext.jobqueue.html) - python-telegram-bot dependency for running scheduled commands

## How to use

To make this bot work in groups you will need to add your bot as administrator of the group and it should have permission to send messages.

To activate bot you should have a `config.py` file with all required parameters (see configuration) and run the following command (example for *NIX systems):

```bash
python -m core [-f]
```

where option `-f`  stand --`fill-none-values`, which will prompt to fill missing values for some schedule info as links, or teacher's info.

## Config

All configuration should be done in a `config.py` file, see `example_config.py` where you can simply put your desired values, or use default ones. So, to set up configuration on *NIX systems you can run:

```bash
cp example_config.py config.py
```

And set all your config in this file. In particural, for this bot to work you must provide the following values:
* AUTH_TOKEN: your bot token
* OVERLORD_USER_ID: the user_id of a person who may control the bot
* URL: the url for the website with your schedule in <table> tags

Other parameters are are set by default, but may change them if you need to. (see example_config.py for all available parameters)

## License

Distributed under the MIT License. See `LICENSE` for more information.

## ROADMAP

* [X] make a proper format messages
* [X] fix scheduler and user commands
* [ ] fix `check_none` function
* [ ] CLEANUP, REFACTORING and DOCUMENTATION

