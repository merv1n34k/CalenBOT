import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    datefmt="%m/%d %H:%M:%S",
    handlers=[
        logging.FileHandler("bot_main.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def log_action(who, what):
    """Print log info in a convinient way."""
    logger.info("%s: %s", who.upper(), what)


