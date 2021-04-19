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
    LAST_FINAL_DATE = "Last Final Date"

    FORECAST = "Forecast"
    FORECAST_PER = "Forecast Percentage"
    MONTHLY_COST = "Monthly Cost"

    MONTHLY_TOTAL_COST = "Monthly Total Cost"
    MONTHLY_TOTAL_COST_MIN = "Monthly Total Cost Min"
    MONTHLY_TOTAL_COST_MAX = "Monthly Total Cost Max"
    MONTHLY_TOTAL_COST_MEAN = "Monthly Total Cost Mean"
    MONTHLY_TOTAL_COST_TOTAL = "Monthly Total Cost Total"
    
    DAILY_COST = "Daily Cost"
    DAILY_TOTAL_COST = "Daily Total Cost"
    DAILY_TOTAL_COST_MIN = "Daily Total Cost Min"
    DAILY_TOTAL_COST_MAX = "Daily Total Cost Max"
    DAILY_TOTAL_COST_MEAN = "Daily Total Cost Mean"
    DAILY_TOTAL_COST_TOTAL = "Daily Total Cost Total"

    SERVICES_COST = "Services Cost"
    SERVICES_TOP_COST = "Top Services"

    ACCOUNTS_COST = "Accounts cost"


@unique
class ItemType(Enum):
    BAR = 'bar'
    LINE = 'line'
    STACK = 'stack'
    PIE = 'pie'
    VALUE = 'value'
