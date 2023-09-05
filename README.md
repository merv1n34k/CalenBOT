# CalenBOT

***ATTENTION!!*** **This project in only in it's alpha version, many things are broken and won't work as expected! The stable version could be released in a few weeks**

A telegram bot for use in groups to send a scheduled messages such as your university's lessons schedule or any other schedules

## Requirements

1. First thing you need is to activate a telegram bot in Telegram's main bot - [@BotFather](https://telegram.me/BotFather)

2. To run this telegram bot, so you will need:

    * [Python](https://www.python.org/) >=3.8
    * [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) >= 20.0.0 (You can use only 20+ versions!) - asynchronous interface for the Telegram Bot API, written in Python
        * [JobQueue](https://docs.python-telegram-bot.org/en/v20.5/telegram.ext.jobqueue.html) - python-telegram-bot dependency for running scheduled commands

## Config

All configuration can be done in a `config.py` file, see `example_config.py` where you can simply put your desired values, or use default ones.

However, in config you **must* provide your bot's *AUTH_TOKEN* and *user_id* of a person who will control the bot (e.g. `/addThisGroup` to allow bot work in group you are sending this command)

Also, you will need to provide a parameters for a schedule, such as:

* List of time of the events
* List of names of the events and other (see `example_config.py` for all parameters)

## How to use

To make this bot work in groups you will need to add your bot as administrator of the group and it should have permission to send messages.

To activate bot you should have a `config.py` file with all parameters and run the following command in your terminal (example for *NIX systems),

```bash
python -m bot_core [-v] [-f] [-s]
```

where options `-v`, `-f` and `-s` stand for `verbose`, `forced` and `strict` respectively.

* `verbose`: increase verbosity
* `forced`: answer `y` for every prompt
* `strict`: raise an error if you directory and/or files are missing, otherwise will create them automatically

## License

Distributed under the MIT License. See `LICENSE` for more information.


