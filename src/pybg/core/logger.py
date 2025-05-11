from aws_lambda_powertools import Logger
from os import getenv

# Initialize the Powertools Logger
logger = Logger(service=getenv("POWERTOOLS_SERVICE_NAME", "pybg"))

# Set the log level from the environment variable, default to ERROR if not set
logger.setLevel(level=getenv("LOG_LEVEL", "DEBUG"))
