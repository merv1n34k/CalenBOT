import logging

class IgnorePostFilter(logging.Filter):
    def filter(self, record):
        return 'HTTP Request: POST' not in record.getMessage()

# Initialize root logging
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

handler1 = logging.StreamHandler()
handler1.setFormatter(logging.Formatter("%(asctime)s %(message)s",datefmt="%m/%d %H:%M:%S"))
handler1.addFilter(IgnorePostFilter())
root_logger.addHandler(handler1)

handler2 = logging.FileHandler("./data/bot.log")
handler2.setFormatter(logging.Formatter("%(asctime)s %(message)s",datefmt="%m/%d %H:%M:%S"))
handler2.addFilter(IgnorePostFilter())
root_logger.addHandler(handler2)

def log_action(who, what):
    """Print log info in a convinient way."""
    root_logger.info("%s: %s", who.upper(), what)
