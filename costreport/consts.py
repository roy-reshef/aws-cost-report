from enum import unique, Enum
from os import environ

# env variables
AWS_ACCESS_KEY_ID = environ.get('AWS_ACCESS_KEY_ID', None)
AWS_SECRET_ACCESS_KEY = environ.get('AWS_SECRET_ACCESS_KEY', None)
REGION_NAME = environ.get('REGION_NAME', None)
LOGGING_LEVEL = environ.get("LOGGING_LEVEL", "INFO")


# TODO: should make configurable
OUTPUT_DIR = 'generated-reports'
CACHE_RESULTS_DIR = '.cache'


@unique
class ReportItemName(Enum):
    CURRENT_DATE = "Current Date"
    FORECAST = "Forecast"
    MONTHLY_COST = "Monthly Cost"
    DAILY_COST = "Daily Cost"
    SERVICES_COST = "Services Cost"
    ACCOUNTS_COST = "Accounts cost"

