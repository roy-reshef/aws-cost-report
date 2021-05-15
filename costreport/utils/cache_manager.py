import logging
import os

from costreport.app_config import AppConfig
from costreport.utils.consts import CACHE_RESULTS_DIR

logger = logging.getLogger(__name__)


class RawDateCacheManager:
    def __init__(self, config: AppConfig, collector_name):
        self.enabled = config.use_cache
        self.collector_cache_dir = f'{CACHE_RESULTS_DIR}_{collector_name}'

        if self.enabled:
            logger.info("cost client will use cached results")
            if not os.path.exists(self.collector_cache_dir):
                os.makedirs(self.collector_cache_dir)

    def save(self, key: str, value: str):
        if self.enabled:
            with open(f'{self.collector_cache_dir}/{key}', 'w') as f:
                f.write(value)

    def get(self, key):
        cached_content = None
        try:
            with open(f'{self.collector_cache_dir}/{key}', 'r') as f:
                cached_content = f.read()
        except Exception as e:
            logger.debug(f'could not load cached key:{key}: {str(e)}')

        return cached_content
