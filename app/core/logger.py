import logging

# Setting up logging
logging.basicConfig(
    level=logging.DEBUG,  
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("main-app.log"), 
        logging.StreamHandler()  
    ]
)

logger = logging.getLogger(__name__)

# Checking logging activities:
logger.debug("This is a debug message")
logger.info("This is an info message")
logger.warning("This is a warning message")
logger.error("This is an error message")
logger.critical("This is a critical message")
