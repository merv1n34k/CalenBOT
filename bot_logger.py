import logging

class IgnorePostFilter(logging.Filter):
    def filter(self, record):
        return 'HTTP Request: POST' not in record.getMessage()

# Initialize root logging
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s %(message)s",datefmt="%m/%d %H:%M:%S"))
handler.addFilter(IgnorePostFilter())
root_logger.addHandler(handler)

def log_action(who, what):
    """Print log info in a convinient way."""
    root_logger.info("%s: %s", who.upper(), what)

#    handlers=[
#        logging.FileHandler("bot.log"),
#        logging.StreamHandler()
#    ]

