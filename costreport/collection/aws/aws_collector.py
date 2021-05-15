import logging
from datetime import datetime
from typing import List

import pandas as pd

from costreport.app_config import AppConfig
from costreport.collection.aws.cost_client import AwsCostClient
from costreport.collection.collector import Collector
from costreport.utils import consts
from costreport.utils.cache_manager import RawDateCacheManager
from costreport.utils.date_utils import get_today, get_months_back, get_days_back, get_first_day_next_month

logger = logging.getLogger(__name__)


class AwsCollector(Collector):
    """
    collector implementation interface
    """

    def __init__(self, config: AppConfig, exec_time: datetime, cache: RawDateCacheManager):
        super().__init__(config, exec_time, cache)
        self.cost_client = AwsCostClient(config, cache)

    def create_data_frame_from_results(self, cost_results):
        """
        returns list of identifiers and dict of values by key
        :param cost_results:
        :return:
        """
        columns = ['dates']
        data_set = {'dates': []}

        for i, v in enumerate(cost_results):
            start = v['TimePeriod']['Start']
            data_set['dates'].append(start)
            current_date_columns = ['dates']

            if v['Groups']:
                for g in v['Groups']:
                    key = g['Keys'][0]
                    # map account id to name:
                    if self.config.accounts and key in self.config.accounts:
                        key = self.config.accounts[key]

                    if not data_set.get(key):
                        # add new column to column list
                        columns.append(key)
                        # initialize array and pad with values if needed
                        data_set[key] = [] if i == 0 else [0] * i

                    current_date_columns.append(key)
                    amount = float(g['Metrics']['UnblendedCost']['Amount'])
                    data_set[key].append(round(amount, 1))

            # get columns in columns list that were not handled in this date and put '0'
            missing = [c for c in columns if c not in current_date_columns]
            for m in missing:
                data_set[m].append(0)

        return pd.DataFrame.from_dict(data_set)

    def get_monthly_report(self) -> pd.DataFrame:
        item_name = consts.ReportItemName.MONTHLY_COST.value
        results = self.cost_client.request_cost_and_usage(
            start=get_months_back(self.config.periods.monthly_report_months_back),
            end=get_today(),
            request_name=item_name,
            group_by_dimensions=['LINKED_ACCOUNT'])

        dataframe = self.create_data_frame_from_results(results)
        return dataframe

    def get_daily_report(self) -> pd.DataFrame:
        item_name = consts.ReportItemName.DAILY_COST.value

        results = self.cost_client.request_cost_and_usage(
            start=get_days_back(self.config.periods.daily_report_days_back),
            end=get_today(),
            request_name=item_name,
            group_by_dimensions=['LINKED_ACCOUNT'],
            granularity='DAILY')

        return self.create_data_frame_from_results(results)

    def get_services_report(self) -> pd.DataFrame:
        item_name = consts.ReportItemName.SERVICES_COST.value
        results = self.cost_client.request_cost_and_usage(
            start=get_days_back(self.config.periods.services_report_days_back),
            end=get_today(),
            request_name=item_name,
            granularity='DAILY',
            group_by_dimensions=['SERVICE'])

        return self.create_data_frame_from_results(results)

    def get_available_tags(self) -> List[str]:
        return self.cost_client.get_available_tags(
            start_date=get_days_back(self.config.periods.tags_report_days_back),
            end_date=get_today())

    def get_tag_report(self, tag_name) -> pd.DataFrame:
        item_name = f"'{tag_name}' Resources Cost"
        results = self.cost_client.request_cost_and_usage(
            start=get_days_back(self.config.periods.tags_report_days_back),
            end=get_today(),
            request_name=item_name,
            granularity='DAILY',
            group_by_tags=[tag_name])
        return self.create_data_frame_from_results(results)

    def get_current_month_forecast(self) -> pd.DataFrame:
        forecast = self.cost_client.get_monthly_cost_forecast(get_today().isoformat(),
                                                              get_first_day_next_month().isoformat())

        return pd.DataFrame.from_dict({'values': [forecast]})
