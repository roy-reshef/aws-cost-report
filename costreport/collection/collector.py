from abc import ABC
from typing import List

import pandas as pd


class Collector(ABC):
    """
    collector implementation interface
    """
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

    def get_tag_report(self, tag_nme) -> pd.DataFrame:
        raise NotImplementedError
