import logging

# Set up logging configuration at the start of the app
logging.basicConfig(
    level=logging.DEBUG,  # Capture DEBUG and above (INFO, WARNING, ERROR, CRITICAL)
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),  # Log to a file
        logging.StreamHandler()  # Log to the console (stdout)
    ]
)

logger = logging.getLogger(__name__)

# Example usage
logger.debug("This is a debug message")
logger.info("This is an info message")
logger.warning("This is a warning message")
logger.error("This is an error message")
logger.critical("This is a critical message")
