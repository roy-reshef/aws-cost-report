import logging

from costreport.consts import LOGGING_LEVEL

logger = logging.getLogger(__name__)
logger.setLevel(LOGGING_LEVEL)
log_handler = logging.StreamHandler()
logger.addHandler(log_handler)
