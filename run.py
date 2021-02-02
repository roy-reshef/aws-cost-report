import json
import logging

from costreport.consts import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, REGION_NAME
from costreport.executors import ScheduledExecutor, SingleExecutor

logger = logging.getLogger(__name__)


def validate_env_variables():
    """
    returns boolean value indicating validity of configuration
    :return:
    """
    valid = True

    if not AWS_ACCESS_KEY_ID:
        logger.error('AWS_ACCESS_KEY_ID environment variable is required for execution')
        valid = False

    if not AWS_SECRET_ACCESS_KEY:
        logger.error('AWS_SECRET_ACCESS_KEY environment variable is required for execution')
        valid = False

    if not REGION_NAME:
        logger.error('REGION_NAME environment variable is required for operation')
        valid = False

    return valid


def _load_config():
    with open('configuration.json', 'r') as c:
        configuration = c.read()

    return json.loads(configuration)


if __name__ == '__main__':
    if not validate_env_variables():
        exit(1)

    config = _load_config()

    if config.get('schedule'):
        executor = ScheduledExecutor(config)
    else:
        executor = SingleExecutor(config)

    executor.exec()
