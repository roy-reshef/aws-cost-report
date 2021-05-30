from abc import ABC
from datetime import datetime
from typing import List

import pandas as pd

from costreport.app_config import AppConfig
from costreport.utils.cache_manager import RawDateCacheManager


class Collector(ABC):
    """
    collector implementation interface
    """

    def __init__(self, config: AppConfig, exec_time: datetime, cache: RawDateCacheManager):
        self.config = config
        self.exec_time = exec_time
        self.cache = cache

    def get_current_month_forecast(self) -> pd.DataFrame:
        raise NotImplementedError

    def get_daily_report(self) -> pd.DataFrame:
        raise NotImplementedError

    def get_monthly_report(self) -> pd.DataFrame:
        raise NotImplementedError

    def get_services_report(self) -> pd.DataFrame:
        raise NotImplementedError

    def get_available_tags(self) -> List[str]:
        raise NotImplementedError

    def get_tag_report(self, tag_name) -> pd.DataFrame:
        raise NotImplementedError
