from enum import unique, Enum
from os import environ

# env variables
AWS_ACCESS_KEY_ID = environ.get('AWS_ACCESS_KEY_ID', None)
AWS_SECRET_ACCESS_KEY = environ.get('AWS_SECRET_ACCESS_KEY', None)
REGION_NAME = environ.get('REGION_NAME', None)

logging_lvl = environ.get("LOGGING_LEVEL")
LOGGING_LEVEL = logging_lvl if logging_lvl else 'INFO'


# TODO: should make configurable
OUTPUT_DIR = 'generated-reports'
CACHE_RESULTS_DIR = '.cache'


@unique
class ReportItemName(Enum):
    REPORT_TITLE = "Report Title"
    CURRENT_DATE = "Current Date"
    FORECAST = "Forecast"
    FORECAST_PER = "Forecast Percentage"
    MONTHLY_COST = "Monthly Cost"

    MONTHLY_TOTAL_COST = "Monthly Total Cost"
    MONTHLY_TOTAL_COST_MIN = "Monthly Total Cost Min"
    MONTHLY_TOTAL_COST_MAX = "Monthly Total Cost Max"
    MONTHLY_TOTAL_COST_MEAN = "Monthly Total Cost Mean"
    MONTHLY_TOTAL_COST_TOTAL = "Monthly Total Cost Total"

    DAILY_COST = "Daily Cost"
    SERVICES_COST = "Services Cost"
    ACCOUNTS_COST = "Accounts cost"


@unique
class ItemType(Enum):
    BAR = 'bar'
    LINE = 'line'
    STACK = 'stack'
    VALUE = 'value'


